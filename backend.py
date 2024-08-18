from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String, Text

app = FastAPI()

DATABASE_URL = "mysql+mysqlconnector://root:mysecretpassword@127.0.0.1/slurm_data"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class SlurmJob(BaseModel):
    slurm_job_id: str
    num_nodes: int

class vClusterStatus(BaseModel):
    num_nodes_total: int | None = None
    num_nodes_allocated: int | None = None
    num_nodes_idle: int | None = None
    num_finished_jobs: int | None = None
    running_jobs: List[SlurmJob] | None = None
    pending_jobs: List[SlurmJob] | None = None

#vcluster_status: Dict[str, vClusterStatus] = {}

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class Item(Base):
    __tablename__ = "vcluster"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    jsondata = Column(Text, index=True)

# TODO: convert dictionary with running/queuing jobs to array with the following values:
# value[0]: number of jobs with 1 node
# value[1]: number of jobs with 2 nodes
# value[2]: number of jobs with 3-4 nodes
# value[3]: number of jobs with 5-8 nodes
# value[4]: number of jobs with 9-16 nodes
# value[5]: number of jobs with 17-32 nodes
# value[6]: number of jobs with 33-64 nodes
# value[7]: number of jobs with 65-128 nodes
# value[8]: number of jobs with 129-256 nodes
# value[9]: number of jobs with > 256 nodes

# TODO: handle properly array jobs

@app.put("/status/{vcluster}")
def put_data(vcluster: str, st: vClusterStatus, db: Session = Depends(get_db)):
#    global vcluster_status
#    vcluster_status[vcluster] = st
    db_item = Item(name=vcluster, jsondata=st.json())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return st

#@app.get("/status/{vcluster}", response_model=vClusterStatus)
#def get_data(vcluster: str):
#    if not vcluster in vcluster_status:
#        raise HTTPException(status_code=404, detail="Item not found")
#    return vcluster_status[vcluster]
#
