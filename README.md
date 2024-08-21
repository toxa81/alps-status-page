# alps-status-page

source ~/envs/nicegui/bin/activate.fish
uvicorn backend:app --reload


curl -X 'PUT' \
                     'http://127.0.0.1:8000/status/eiger' \
                     -H 'accept: application/json' \
                     -H 'Content-Type: application/json' \
                     -d '{"num_nodes_total" : 4}'


# DB deployment

## Create docker volume
docker volume create slurm_data

## run mysql container
docker run --name mysql_db -e MYSQL_ROOT_PASSWORD=mysecretpassword -p 3306:3306 --mount type=volume,source=slurm_data,target=/var/lib/mysql -d mysql:latest

## create table
docker exec -it mysql_db mysql -u root -p
create database: `CREATE DATABASE slurm_data;`
use database: `USE slurm_data;`
create table: `CREATE TABLE vcluster (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(50) NOT NULL, jsondata TEXT NOT NULL, datetime TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL);`

to remove table: `DROP TABLE IF EXISTS vcluster;`

