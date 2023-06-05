# Entrebiz

* Python 3.8 >=
* PostgresQL
* Celery
* AWS S3
### Install Redis
#### Refer below link
https://www.digitalocean.com/community/tutorials/how-to-install-and-secure-redis-on-ubuntu-18-04
### Run Celery
 `celery -A entrebiz  worker -B -l info`

#### Initial Data 
Initial data need to be added in database in order to run the application properly.
1. Go to directory `entrebiz/initial_data`
2. run `export DJANGO_SETTINGS_MODULE=entrebiz.settings `
3. run each scripts : `python <script_name>`