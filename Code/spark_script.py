from pyspark.sql import SparkSession
from pyspark.sql.types import *
from pyspark.sql.functions import *

# NOTE: This variable needs to be reviewed if we are working with a new MSK
BOOTSTRAP_SERVERS='localhost:9092'

if __name__ == "__main__":
    spark = SparkSession.builder.getOrCreate()

    # NOTE: we cant load the schema file from the local machine anymore, so we have to pull it from s3
    schema = spark.read.json('s3a://air-stream/artifacts/air_stream_schema.json').schema

    # We have to connect to the bootstrap servers, instead of kafka:9092
    df = spark \
        .readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", BOOTSTRAP_SERVERS) \
        .option("subscribe", "dbserver1.air_stream_db.air_stream") \
        .option("startingOffsets", "latest") \
        .load()

    transform_df = df.select(col("value").cast("string")).alias("value").withColumn("jsonData",from_json(col("value"),schema)).select("jsonData.payload.after.*")

    # NOTE: We cannot checkpoint to a local machine because we are working on the cloud. S3 is a reliable location for the cluster
    checkpoint_location = "s3a://air-stream/sparkStreaming_checkpoints/"

    # define hudi parameters
    table_name = 'air_stream'
    hudi_options = {
        'hoodie.table.name': table_name,
        "hoodie.datasource.write.table.type": "COPY_ON_WRITE",
        'hoodie.datasource.write.recordkey.field': 'record_id',
        'hoodie.datasource.write.partitionpath.field': 'flight_iata', # partition by flight number
        'hoodie.datasource.write.table.name': table_name,
        'hoodie.datasource.write.operation': 'upsert',
        'hoodie.datasource.write.precombine.field': 'updated',
        'hoodie.upsert.shuffle.parallelism': 100,
        'hoodie.insert.shuffle.parallelism': 100
    }

    # the input location of the data
    s3_path = "s3a://air-stream/air_streaming_data/"

    # define how to write the data into S3 output
    def write_batch(batch_df, batch_id):
        batch_df.write.format("org.apache.hudi") \
        .options(**hudi_options) \
        .mode("append") \
        .save(s3_path)

    # call the write function
    transform_df.writeStream.option("checkpointLocation", checkpoint_location).queryName("air-streaming").foreachBatch(write_batch).start().awaitTermination()