import logging
import json
import os
import re

from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Optional, Any

from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.exc import NoSuchTableError
from sqlalchemy import MetaData, Table, Column, Integer, String, Text, TIMESTAMP, func, create_engine, select

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

logger = logging.getLogger(__name__)

app = FastAPI()

#DATABASE_URL = "mysql+mysqlconnector://root:rNAFFABczJs5hWuyyNbAEKgYD@127.0.0.1/slurm_data"
#engine = create_engine(DATABASE_URL)

engine = create_engine(os.environ['DATABASE_URL'])
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
metadata = MetaData()
metadata.reflect(bind=engine)

def get_table_by_name(table_name: str):
    try:
        table = Table(
            table_name,
            metadata,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('jsondata', Text, nullable=False),
            Column('datetime', TIMESTAMP, nullable=False),
            autoload_with=engine,
            extend_existing=True
        )
        return table
    except NoSuchTableError:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' does not exist")


class SlurmJob(BaseModel):
    slurm_job_id: str
    num_nodes: int

# this data comes in from the bash script executed on the login node of a vcluster
class vClusterStatusIn(BaseModel):
    num_nodes_gross: int | None = None
    num_nodes_total: int | None = None
    num_nodes_allocated: int | None = None
    num_nodes_idle: int | None = None
    num_finished_jobs: int | None = None
    running_jobs: List[SlurmJob] | None = None
    pending_jobs: List[SlurmJob] | None = None
    finished_job_times: List[List[int]] | None = None

# generic data dictionary that is sent as a response
class vClusterStatusOut(BaseModel):
    body: Dict[str, Any]
    datetime: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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
def put_status(vcluster: str, st: vClusterStatusIn, db: Session = Depends(get_db)):
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
        else:
            njobs = 1
        pj_hist[get_index(e["num_nodes"])] += njobs

    d["running_jobs"] = rj_hist
    d["pending_jobs"] = pj_hist

    try:
        table = get_table_by_name(f"vcluster_{vcluster}")
        insert_stmt = table.insert().values(jsondata=json.dumps(d, indent=2))
        db.execute(insert_stmt)
        db.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return st

@app.get("/status/{vcluster}", response_model=vClusterStatusOut)
def get_status(vcluster: str, db: Session = Depends(get_db)):
    try:
        table = get_table_by_name(f"vcluster_{vcluster}")
        select_stmt = select(table).order_by(table.c.datetime.desc()).limit(1)
        result = db.execute(select_stmt).fetchone()
        if result:
            return vClusterStatusOut(body=json.loads(result.jsondata), datetime=result.datetime.isoformat())
        else:
            raise HTTPException(status_code=404, detail="Record not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/history/{vcluster}", response_model=vClusterStatusOut)
def get_history(vcluster: str, db: Session = Depends(get_db)):
    N = 4320 # example value for N (3 days in the past)
    time_now = datetime.now()
    time_begin = time_now - timedelta(minutes=N)
    try:
        table = get_table_by_name(f"vcluster_{vcluster}")
        select_stmt = (
            select(table)
            .where(table.c.datetime.between(time_begin, time_now))
            .order_by(table.c.datetime)
        )
        results = db.execute(select_stmt).fetchall()
        if not results:
            raise HTTPException(status_code=404, detail="SQL query failed")

        time_shift = []
        num_nodes_total = []
        num_nodes_allocated = []
        num_nodes_idle = []
        for e in results:
            d = json.loads(e[1])
            time_shift.append((e[2] - time_now).total_seconds() / 60 / 60)
            num_nodes_total.append(d["num_nodes_total"])
            num_nodes_allocated.append(d["num_nodes_allocated"])
            num_nodes_idle.append(d["num_nodes_idle"])
        
        return vClusterStatusOut(body={"count": len(results), "time_shift": time_shift,
                                       "num_nodes_total": num_nodes_total,
                                       "num_nodes_allocated": num_nodes_allocated,
                                       "num_nodes_idle": num_nodes_idle}, datetime=time_now.isoformat())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


