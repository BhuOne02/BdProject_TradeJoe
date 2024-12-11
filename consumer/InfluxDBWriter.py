from pyspark.sql import Row
from pyspark.sql.functions import *
from pyspark.sql.types import *
from datetime import datetime, timedelta

import influxdb_client 
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client import Point, WritePrecision
import os

class InfluxDBWriter:
    def __init__(self, bucket, measurement):
        self.bucket = bucket
        self.measurement = measurement
        self.client = influxdb_client.InfluxDBClient(url="http://influxdb:8086", 
                    token=os.environ.get("INFLUX_TOKEN"),
                    org=os.environ.get("INFLUX_ORG")
                    )
        self.is_connected()
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)

    def open(self, partition_id, epoch_id):
        print("Opened %d, %d" % (partition_id, epoch_id))
        return True

    # def process(self, row):
    def process(self, timestamp, tags, fields):
        print("inside process")
        point = Point(self.measurement)

        for key, value in tags.items():
            point.tag(key, value)

        # Add fields to the Point
        for key, value in fields.items():
            point.field(key, value)

        point.time(timestamp, WritePrecision.S)
        self.write_api.write(bucket=self.bucket, record=point)

    def close(self, error):
        self.write_api.__del__()
        self.client.__del__()
        print("Closed with error: %s" % str(error))

    def row_to_line_protocol(measurement, tags, fields, timestamp):
        """
        Convert a row into InfluxDB Line Protocol format.

        Args:
        - measurement (str): The measurement name.
        - tags (dict): A dictionary of tag key-value pairs.
        - fields (dict): A dictionary of field key-value pairs.
        - timestamp (int): The timestamp in Unix epoch format (milliseconds).

        Returns:
        - str: The InfluxDB Line Protocol string.
        """
        # Convert tags to a comma-separated string
        tag_str = ",".join([f"{k}={v}" for k, v in tags.items()])

        # Convert fields to a comma-separated string
        field_str = ",".join([f"{k}={v}" for k, v in fields.items()])

        # Combine measurement, tags, fields, and timestamp
        line_protocol = f"{measurement}{',' + tag_str if tag_str else ''} {field_str} {timestamp}"

        return line_protocol
    
    def is_connected(self):
        try:
            health = self.client.health()
            if health.status == "pass":
                print("InfluxDB health check passed.")
                return True
            else:
                print(f"InfluxDB health check failed: {health.message}")
                return False
        except Exception as e:
            print(f"Exception during InfluxDB health check: {e}")
            return False
