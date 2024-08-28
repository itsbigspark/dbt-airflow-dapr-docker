FROM python:3.11
RUN pip install --upgrade pip && \
pip install wtforms==2.3.3 && \
    pip install 'apache-airflow[postgres]==2.7.3' && \
    pip install dbt-postgres==1.5.9 && \
    pip install SQLAlchemy==1.4.49 && \
    pip install flask-session==0.3.2

RUN mkdir /project
COPY scripts_airflow/ /project/scripts/

RUN chmod +x /project/scripts/init.sh
ENTRYPOINT [ "/project/scripts/init.sh" ]