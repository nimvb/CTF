import itertools
import json
import string

import pika

NOTIFY_QUEUE_NAME = "ACCOMPLISHED"
FIRST_QUEUE_NAME = "agent-1"
SECOND_QUEUE_NAME = "agent-2"
THIRD_QUEUE_NAME = "agent-3"
SERVER_IP = "#RABBITMQ_SERVER_ADDRESS#"
USERNAME = "#USERNAME#"
PASSWORD = "#PASSWORD#"
SERVER_PORT = 5672

routings = [FIRST_QUEUE_NAME, SECOND_QUEUE_NAME, THIRD_QUEUE_NAME]

channel = None


def generate_dictionary(r=3):
    # 0.
    alphabet = string.ascii_letters + "_-+*?@!#%&^()[]{}\|/,.:;~<>=" + string.digits + " "

    # 1. Generate all three letter words
    three_letter_words = [''.join(w) for w in itertools.product(alphabet, repeat=r)]

    # 2. Join each word with 'm0vfu3c4t0r!'
    words = [w + 'm0vfu3c4t0r!' for w in three_letter_words]

    return words


def distribute_data():
    global routings
    connection = pika.BlockingConnection(pika.ConnectionParameters(SERVER_IP, SERVER_PORT, virtual_host="/",
                                                                   credentials=pika.PlainCredentials(USERNAME,
                                                                                                     PASSWORD)))
    channel = connection.channel()

    for queue in routings:
        channel.queue_declare(queue)

    dictionary = generate_dictionary()

    print "[*] Total array length : " + str(len(dictionary))

    part_size = (len(dictionary) / len(routings))

    sub_dictionaries = [dictionary[i:i + part_size] for i in range(0, len(dictionary), part_size)]

    i = 0
    for sub_dict in sub_dictionaries:
        msg = json.dumps(sub_dict)
        channel.basic_publish(exchange='', routing_key=routings[i], body=msg)
        i = (i + 1) % len(routings)

    connection.close()


def notify_callback(ch, method, properties, body):
    global channel
    message = str(body)
    print("[*] Notified! %s" % (message))
    channel.stop_consuming()


def wait_for_notify():
    global channel
    connection = pika.BlockingConnection(pika.ConnectionParameters(SERVER_IP, SERVER_PORT, virtual_host="/",
                                                                   credentials=pika.PlainCredentials(USERNAME,
                                                                                                     PASSWORD)))
    channel = connection.channel()

    channel.queue_declare(NOTIFY_QUEUE_NAME)

    channel.basic_consume(notify_callback,
                          queue=NOTIFY_QUEUE_NAME,
                          no_ack=True)

    print('[*] Waiting for notify message ...')
    channel.start_consuming()


def notify_agents():
    global routings
    connection = pika.BlockingConnection(pika.ConnectionParameters(SERVER_IP, SERVER_PORT, virtual_host="/",
                                                                   credentials=pika.PlainCredentials(USERNAME,
                                                                                                     PASSWORD)))
    channel = connection.channel()

    for queue in routings:
        channel.queue_declare(queue)

    for queue in routings:
        channel.basic_publish(exchange='', routing_key=queue, body="***TERMINATE***")
    connection.close()


if __name__ == "__main__":
    distribute_data()
    wait_for_notify()
    notify_agents()
