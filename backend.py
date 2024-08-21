import logging
import json
import os
import re

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Optional, Any

from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, func, create_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

logger = logging.getLogger(__name__)

app = FastAPI()

#DATABASE_URL = "mysql+mysqlconnector://root:mysecretpassword@127.0.0.1/slurm_data"

engine = create_engine(os.environ['DATABASE_URL'])
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class SlurmJob(BaseModel):
    slurm_job_id: str
    num_nodes: int

class vClusterStatusIn(BaseModel):
    num_nodes_total: int | None = None
    num_nodes_allocated: int | None = None
    num_nodes_idle: int | None = None
    num_finished_jobs: int | None = None
    running_jobs: List[SlurmJob] | None = None
    pending_jobs: List[SlurmJob] | None = None

class vClusterStatusOut(BaseModel):
    num_nodes_total: int | None = None
    num_nodes_allocated: int | None = None
    num_nodes_idle: int | None = None
    num_finished_jobs: int | None = None
    running_jobs: List[int] | None = None
    pending_jobs: List[int] | None = None

class vClusterStatusOut_v2(BaseModel):
    body: Dict[str, Any]
    datetime: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class Item(Base):
    __tablename__ = "vcluster"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    jsondata = Column(Text, nullable=False)
    datetime = Column(TIMESTAMP, server_default=func.now(), nullable=False)

def get_index(num_nodes):
# index 0: number of jobs with 1 node
# index 1: number of jobs with 2 nodes
# index 2: number of jobs with 3-4 nodes
# index 3: number of jobs with 5-8 nodes
# index 4: number of jobs with 9-16 nodes
# index 5: number of jobs with 17-32 nodes
# index 6: number of jobs with 33-64 nodes
# index 7: number of jobs with 65-128 nodes
# index 8: number of jobs with 129-256 nodes
# index 9: number of jobs with > 256 nodes
    ranges = {
        range(1, 2): 0,
        range(2, 3): 1,
        range(3, 5): 2,
        range(5, 9): 3,
        range(9, 17): 4,
        range(17, 33): 5,
        range(33, 65): 6,
        range(65, 129): 7,
        range(129, 257): 8
    }
    for r, index in ranges.items():
        if num_nodes in r:
            return index
    return 9


@app.put("/status/{vcluster}")
def put_data(vcluster: str, st: vClusterStatusIn, db: Session = Depends(get_db)):
    d = st.dict()

    rj_hist = [0 for i in range(10)]
    for e in d["running_jobs"]:
        rj_hist[get_index(e["num_nodes"])] += 1

    pj_hist = [0 for i in range(10)]
    for e in d["pending_jobs"]:
        job_id = e["slurm_job_id"]
        match = re.search(r'\[(\d+)-(\d+)\]', job_id)
        if match:
            lower_bound = int(match.group(1))
            upper_bound = int(match.group(2))
            njobs = upper_bound - lower_bound + 1
            logger.info(f"array job: {lower_bound} {upper_bound} {njobs}")
        else:
            njobs = 1
        pj_hist[get_index(e["num_nodes"])] += njobs

    d["running_jobs"] = rj_hist
    d["pending_jobs"] = pj_hist

    db_item = Item(name=vcluster, jsondata=json.dumps(d, indent=2))
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    logger.info(f"running jobs histogram: {rj_hist}")
    logger.info(f"pending jobs histogram: {pj_hist}")
    return st

@app.get("/status/{vcluster}", response_model=vClusterStatusOut_v2)
def get_data(vcluster: str, db: Session = Depends(get_db)):
    try:
        record = (
            db.query(Item)
            .filter(Item.name == vcluster)
            .order_by(Item.datetime.desc())
            .first()
        )
        if not record:
            raise HTTPException(status_code=404, detail="Record not found")
        return vClusterStatusOut_v2(body=json.loads(record.jsondata), datetime=record.datetime.isoformat())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


