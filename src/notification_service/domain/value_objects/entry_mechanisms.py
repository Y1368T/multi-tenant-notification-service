from enum import Enum
class EntryMechanism(Enum):
    REST = "rest"
    KAFKA = "kafka"
    RABBITMQ = "rabbitmq"
    GRPC = "grpc"