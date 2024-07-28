from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional

app = FastAPI()

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

vcluster_status: Dict[str, vClusterStatus] = {}

@app.put("/status/{vcluster}")
def put_data(vcluster: str, st: vClusterStatus):
    global vcluster_status
    vcluster_status[vcluster] = st
    return st

@app.get("/status/{vcluster}", response_model=vClusterStatus)
def get_data(vcluster: str):
    if not vcluster in vcluster_status:
        raise HTTPException(status_code=404, detail="Item not found")
    return vcluster_status[vcluster]

