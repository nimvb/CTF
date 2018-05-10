import commands
import json
import threading
from datetime import datetime

import pika

DESKTOP_PATH = "~/Desktop/"
BINARY_PATH = DESKTOP_PATH + "babyc"
PIN_BASE_PATH = DESKTOP_PATH + "pin-3.6-97554-g31f0a167d-gcc-linux/"
PIN_PATH = PIN_BASE_PATH + "pin"
PIN_TOOL_BASE_PATH = PIN_BASE_PATH + "source/tools/ManualExamples/obj-ia32/"
PIN_TOOL_PATH = PIN_TOOL_BASE_PATH + "inscount2.so"
SERVER_IP = "#RABBITMQ_SERVER_ADDRESS#"
USERNAME = "#USERNAME#"
PASSWORD = "#PASSWORD#"
QUEUE_NAME = "#QUEUE_NAME#"
SERVER_PORT = 5672
NOTIFY_QUEUE_NAME = "ACCOMPLISHED"
SUBLIST_ITEM_COUNT = 1500
agent_managers = []
agent_results = {}

finish = 0
channel = None


def run_program(command):
    return commands.getoutput(command)


def run_pin_tool(input):
    count = 0

    # 1. Run pintool

    cmd = ["echo '%s' | %s -t %s -- %s" % (input, PIN_PATH, PIN_TOOL_PATH, BINARY_PATH)]

    out = run_program(cmd[0])

    # 2. Get number of executed instructions

    try:
        count = long(out.strip("Wrong!"))
    except:
        pass

    return count


def agent(dictionary, results, id):
    global finish
    print "[X] Agent %d started ..." % (id)
    times = 0
    count = 0
    answer = ""
    for word in dictionary:
        if finish == 1:
            break

        current_count = run_pin_tool(word)
        diff = current_count - count

        if diff >= 20:
            count = current_count
            answer = word
            if times == 1:
                print "[XXX] %s -> %d\n" % (word, current_count)
                notify_manager(word + ":" + str(current_count))
            times = 1

    result = {count: answer}
    results[id] = result


def agent_manager(dictionary):
    global agent
    agents = []
    sub_dictionaries = [dictionary[i:i + SUBLIST_ITEM_COUNT] for i in range(0, len(dictionary), SUBLIST_ITEM_COUNT)]
    agent_id = 0
    for sub_dictionary in sub_dictionaries:
        agents.append(threading.Thread(target=agent, args=(sub_dictionary, agent_results, agent_id)))
        agent_id += 1

    for a in agents:
        a.start()

    for a in agents:
        a.join()

    print agent_results


def callback(ch, method, properties, body):
    global finish
    global channel
    global agent_manager
    global agent_managers

    print("[X] GOT NEW MESSAGE!")

    if str(body).startswith("***TERMINATE***"):
        print("[X] Exiting ... ")
        channel.stop_consuming()
        finish = 1
        return

    dictionary = json.loads(body)
    manager = threading.Thread(target=agent_manager, args=(dictionary,))
    agent_managers.append(manager)
    manager.start()


def consumer():
    global channel

    connection = pika.BlockingConnection(pika.ConnectionParameters(SERVER_IP, SERVER_PORT, virtual_host="/",
                                                                   credentials=pika.PlainCredentials(USERNAME,
                                                                                                     PASSWORD)))
    channel = connection.channel()

    channel.queue_declare(QUEUE_NAME)

    channel.basic_consume(callback,
                          queue=QUEUE_NAME,
                          no_ack=True)

    print('[X] Waiting ...')
    channel.start_consuming()


def notify_manager(answer):
    connection = pika.BlockingConnection(pika.ConnectionParameters(SERVER_IP, SERVER_PORT, virtual_host="/",
                                                                   credentials=pika.PlainCredentials(USERNAME,
                                                                                                     PASSWORD)))
    channel = connection.channel()
    channel.queue_declare(NOTIFY_QUEUE_NAME)

    channel.basic_publish(exchange='', routing_key=NOTIFY_QUEUE_NAME, body=answer)
    connection.close()


if __name__ == "__main__":
    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("[X] START TIME <===> %s [X]" % (start_time))
    consumer()
    for am in agent_managers:
        am.join()
    end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("[X] END TIME <===> %s [X]" % (end_time))
