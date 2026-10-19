import json
import random
import uuid
import time
from datetime import datetime, timedelta, timezone
from kafka import KafkaProducer
import os

import json
import random
import uuid
import time
from datetime import datetime, timedelta, timezone
from kafka import KafkaProducer
import os
from dotenv import load_dotenv

load_dotenv()

#Configuration for EventHub
producer = KafkaProducer(
    bootstrap_servers=f"{os.getenv('AZURE_EVENTHUBS_NAMESPACE')}:9093",
    security_protocol='SASL_SSL',
    sasl_mechanism="PLAIN",
    sasl_plain_username="$ConnectionString",
    sasl_plain_password=os.getenv("AZURE_CONNECTION_STRING"),
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# Departments in hospital
departments = ['Emergency', 'Surgery', 'ICU', 'Pediatrics', 'Maternity', 'Oncology', 'Cardiology']

genders = ['Male','Female']
# Helper functions to introduce messy data on a less than 5% chance rate
def inject_messy_data(record):
    if random.random() < 0.05:
        record['admission_time'] = (datetime.now(timezone.utc) + timedelta(hours=random.randint(0, 72))).isoformat()

    if random.random() < 0.05:
        record['age'] = random.randint(105, 150)

    return record

def generate_patient_event():
    # Create a random admission time: subtract now from a random date(now to 72 hours ago)
    admission_time = datetime.now(timezone.utc) - timedelta(hours=random.randint(0, 72))
    # Create random discharge time: From admission_time add a random date(one hour to 72 hours from now)
    discharge_time = admission_time + timedelta(hours=random.randint(1, 72))

    # Generating an event with randomized values
    event = {
        'patient_id': str(uuid.uuid4()),
        'gender': random.choice(genders),
        'age': random.randint(1,100),
        'department': random.choice(departments),
        'admission_time': admission_time.isoformat(),
        'discharge_time': discharge_time.isoformat(),
        'bed_id': random.randint(1, 500),
        'hospital_id': random.randint(1, 7)
    }

    return inject_messy_data(event)


if __name__=='__main__':
    while True:
        event = generate_patient_event()
        producer.send(os.getenv("AZURE_EVENT_HUB_NAME"), event)
        print(f"Sent to Event Hub: {event}")
        time.sleep(1)