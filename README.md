# alps-status-page

source ~/envs/nicegui/bin/activate.fish
uvicorn backend:app --reload


curl -X 'PUT' \
                     'http://127.0.0.1:8000/status/eiger' \
                     -H 'accept: application/json' \
                     -H 'Content-Type: application/json' \
                     -d '{"num_nodes_total" : 4}'


# DB deployment
docker volume create slurm_data
