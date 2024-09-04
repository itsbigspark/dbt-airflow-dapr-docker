FROM python:3.11
RUN pip install --upgrade pip && \
pip install wtforms==2.3.3 && \
    pip install 'apache-airflow[postgres]==2.10.0' && \
    pip install dbt-postgres==1.5.9 && \
    pip install SQLAlchemy==1.4.49 && \
    pip install astronomer-cosmos && \
    pip install apache-airflow-providers-openlineage

#AWS specifics
RUN pip install boto3 && \
    pip install botocore && \
    pip install paramiko

RUN mkdir /project
COPY scripts/ /project/scripts/

RUN chmod +x /project/scripts/init.sh
ENTRYPOINT [ "/project/scripts/init.sh" ]