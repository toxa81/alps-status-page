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

engine = create_engine(os.environ['DATABASE_URL'], pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
metadata = MetaData()
metadata.reflect(bind=engine)

def get_table_by_name(table_name: str):
    try:
        table = Table(
            table_name,
            metadata,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('label', Text, nullable=False),
            Column('jsondata', Text, nullable=False),
            Column('datetime', TIMESTAMP, nullable=False),
            autoload_with=engine,
            extend_existing=True
        )
        return table
    except NoSuchTableError:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' does not exist")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_index(num_nodes):
    '''
    Get index of the job bin by the number of nodes job requests

    index 0: job with 1 node
    index 1: job with 2 nodes
    index 2: job with 3-4 nodes
    index 3: job with 5-8 nodes
    index 4: job with 9-16 nodes
    index 5: job with 17-32 nodes
    index 6: job with 33-64 nodes
    index 7: job with 65-128 nodes
    index 8: job with 129-256 nodes
    index 9: job with > 256 nodes
    '''
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


# save any single measurement to DB
@app.put("/api/{vcluster}/{label}")
def put_measurement(vcluster: str, label: str, payload: Dict, db: Session = Depends(get_db)):

    # slurm data requires special handlig
    if label == 'slurm-info':

        # running jobs histogram
        rj_hist = [0 for i in range(10)]
        for e in payload.get('running_jobs', []):
            rj_hist[get_index(e['num_nodes'])] += 1

        # pending jobs histogram
        pj_hist = [0 for i in range(10)]
        for e in payload.get('pending_jobs', []):
            job_id = e['slurm_job_id']
            # look for the array job
            match = re.search(r'\[(\d+)-(\d+)\]', job_id)
            if match:
                lower_bound = int(match.group(1))
                upper_bound = int(match.group(2))
                njobs = upper_bound - lower_bound + 1
            else:
                njobs = 1
            pj_hist[get_index(e["num_nodes"])] += njobs

        # substitute data
        payload['running_jobs'] = rj_hist
        payload['pending_jobs'] = pj_hist

    try:
        table = get_table_by_name(f"vcluster_{vcluster}")
        insert_stmt = table.insert().values(label=label, jsondata=json.dumps(payload, indent=2))
        db.execute(insert_stmt)
        db.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return payload

@app.get("/api/{vcluster}/{label}", response_model=Dict)
def get_measurement(vcluster: str, label: str, db: Session = Depends(get_db)):
    try:
        table = get_table_by_name(f"vcluster_{vcluster}")
        select_stmt = select(table).filter(table.c.label == label).order_by(table.c.datetime.desc()).limit(1)
        result = db.execute(select_stmt).fetchone()
        if result:
            return {'body': json.loads(result.jsondata), 'datetime': result.datetime.isoformat()}
        else:
            raise HTTPException(status_code=404, detail='Record not found')
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/{vcluster}/scratch-response/history", response_model=Dict)
def get_scratch_time_history(vcluster: str, db: Session = Depends(get_db)):
    N = 4320 # example value for N (3 days in the past)
    time_now = datetime.now()
    time_begin = time_now - timedelta(minutes=N)
    try:
        table = get_table_by_name(f"vcluster_{vcluster}")
        select_stmt = (
            select(table)
            .where(table.c.datetime.between(time_begin, time_now), table.c.label == 'scratch-response')
            .order_by(table.c.datetime.desc())
        )
        results = db.execute(select_stmt).fetchall()
        if not results:
            raise HTTPException(status_code=404, detail="SQL query failed")

        time_shift = []
        real_time = []
        sys_time = []
        for e in results:
            d = json.loads(e[2])
            time_shift.append((e[3] - time_now).total_seconds() / 60 / 60)
            real_time.append(d['real'])
            sys_time.append(d['sys'])
        return_result = {}
        return_result['count'] = len(results)
        return_result['time_shift'] = time_shift
        return_result['real_time'] = real_time
        return_result['sys_time'] = sys_time
        return {"body": return_result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/{vcluster}/slurm-info/history", response_model=Dict)
def get_slurm_history(vcluster: str, db: Session = Depends(get_db)):
    N = 4320 # example value for N (3 days in the past)
    time_now = datetime.now()
    time_begin = time_now - timedelta(minutes=N)
    try:
        table = get_table_by_name(f"vcluster_{vcluster}")
        select_stmt = (
            select(table)
            .where(table.c.datetime.between(time_begin, time_now), table.c.label == 'slurm-info')
            .order_by(table.c.datetime.desc())
        )
        results = db.execute(select_stmt).fetchall()
        if not results:
            raise HTTPException(status_code=404, detail="SQL query failed")

        time_shift = []
        num_nodes_total = []
        num_nodes_allocated = []
        num_nodes_idle = []
        for e in results:
            d = json.loads(e[2])
            time_shift.append((e[3] - time_now).total_seconds() / 60 / 60)
            num_nodes_total.append(d['num_nodes_total'])
            num_nodes_allocated.append(d['num_nodes_allocated'])
            num_nodes_idle.append(d['num_nodes_idle'])
        return_result = {}
        return_result['count'] = len(results)
        return_result['time_shift'] = time_shift
        return_result['num_nodes_total'] = num_nodes_total
        return_result['num_nodes_allocated'] = num_nodes_allocated
        return_result['num_nodes_idle'] = num_nodes_idle
        return {"body": return_result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/{vcluster}/{label}/{N}", response_model=Dict)
def get_measurements(vcluster: str, label: str, N: int, db: Session = Depends(get_db)):
    try:
        table = get_table_by_name(f"vcluster_{vcluster}")
        select_stmt = select(table).filter(table.c.label == label).order_by(table.c.datetime.desc()).limit(N)
        result = db.execute(select_stmt).fetchall()
        if result:
            return_result = {"body" : []}
            for r in result:
                tmp = json.loads(r.jsondata)
                tmp['datetime'] = r.datetime.isoformat()
                return_result["body"].append(tmp)
            return return_result
        else:
            raise HTTPException(status_code=404, detail="Record not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

