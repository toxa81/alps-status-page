# alps-status-page

source ~/envs/nicegui/bin/activate.fish
uvicorn backend:app --reload


curl -X 'PUT' \
                     'http://127.0.0.1:8000/status/eiger' \
                     -H 'accept: application/json' \
                     -H 'Content-Type: application/json' \
                     -d '{"num_nodes_total" : 4}'


# DB deployment

# How to initialize the project
To deploy first time, the following requirements and steps must be complete:
 - `docker` is available
 - admin password for mysql DB is set: `export MYSQL_ROOT_PASSWORD=...`
 - docker volume to store measured data is created: `docker volume create vcluster_data`
 - run a container with mysql and mounted voulume: `docker run --name mysql-db -e MYSQL_ROOT_PASSWORD=$MYSQL_ROOT_PASSWORD -p 3306:3306 --mount type=volume,source=vcluster_data,target=/var/lib/mysql -d mysql:latest`
 - login into mysql to create database and tables: `docker exec -it mysql-db mysql -u root -p$MYSQL_ROOT_PASSWORD`
 - create database: `CREATE DATABASE vcluster_data;`, then `USE vcluster_data;`
 - create initial tables for each vcluster

## Initialisation of tables
`CREATE TABLE vcluster_eiger ( id INT AUTO_INCREMENT PRIMARY KEY, label VARCHAR(50) NOT NULL, jsondata LONGTEXT NOT NULL, datetime TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL, INDEX idx_datetime (datetime), INDEX idx_label (label) );`



## Create docker volume
docker volume create slurm_data

## run mysql container
docker run --name mysql_db -e MYSQL_ROOT_PASSWORD=mysecretpassword -p 3306:3306 --mount type=volume,source=slurm_data,target=/var/lib/mysql -d mysql:latest

## create table
docker exec -it mysql_db mysql -u root -p
create database: `CREATE DATABASE slurm_data;`
use database: `USE slurm_data;`
create table: `CREATE TABLE vcluster (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(50) NOT NULL, jsondata TEXT NOT NULL, datetime TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL);`

CREATE TABLE vcluster_daint (id INT AUTO_INCREMENT PRIMARY KEY, jsondata LONGTEXT NOT NULL, datetime TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL, INDEX idx_datetime (datetime));
CREATE TABLE vcluster_eiger (id INT AUTO_INCREMENT PRIMARY KEY, jsondata LONGTEXT NOT NULL, datetime TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL, INDEX idx_datetime (datetime));
CREATE TABLE vcluster_todi (id INT AUTO_INCREMENT PRIMARY KEY, jsondata LONGTEXT NOT NULL, datetime TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL, INDEX idx_datetime (datetime));
CREATE TABLE vcluster_bristen (id INT AUTO_INCREMENT PRIMARY KEY, jsondata LONGTEXT NOT NULL, datetime TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL, INDEX idx_datetime (datetime));

to remove table: `DROP TABLE IF EXISTS vcluster;`

