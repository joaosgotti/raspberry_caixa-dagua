import paho.mqtt.client as mqtt


class MqttBaseDevice(object):

    def __init__(self, server="test.mosquitto.org"):
        super(MqttBaseDevice, self).__init__()
        self.client = None
        self.topic = "/service/%s" % 'c8fc7f8f-53d4-4457-9da1-478e99b1c87f'
        self.server = server
        self.last_will_topic = None
        self.last_will = None
        self.username = None
        self.password = None
        self.port = 1883

    def loop_start(self):
        self.create_client()
        self.client.loop_start()

    def loop_forever(self):
        self.create_client()
        self.client.loop_forever()

    def create_client(self):
        self.client = mqtt.Client()
        if self.username is not None and self.password is not None:
            self.client.username_pw_set(self.username, self.password)
        if self.last_will_topic is not None:
            self.client.will_set(self.last_will_topic, self.last_will)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(self.server, self.port, 60)
        # self.client.connect("iot.eclipse.org", 1883, 60)
        # self.client.connect("192.168.8.1", 1883, 60)

    def on_message(self, client, user_data, msg):
        pass

    # def _on_connect(self, client, userdata, flags, rc):
    #     self.on_connect(client, userdata, flags, rc)
    #
    # def _on_message(self, client, userdata, msg):
    #     self.on_message(client, userdata, msg)

    # The callback for when the client receives a CONNACK response from the server.
    def on_connect(self, client, user_data, flags, rc):
        print("Connected with result code " + str(rc))
