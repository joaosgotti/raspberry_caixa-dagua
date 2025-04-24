from .mqtt_base_device import MqttBaseDevice


class MqttBaseListener(MqttBaseDevice):

    def __init__(self, server="test.mosquitto.org",
                 topic="/service/%s" % 'c8fc7f8f-53d4-4457-9da1-478e99b1c87f'):
        super(MqttBaseListener, self).__init__(server)
        self.client = None
        self.topic = topic

    # The callback for when the client receives a CONNACK response from the server.
    def on_connect(self, client, user_data, flags, rc):
        super(MqttBaseListener, self).on_connect(client, user_data, flags, rc)

        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        self.client = client
        self.client.subscribe(self.topic)
        print("subscribed to:", self.get_topic_name())

    def get_topic_name(self):
        return self.topic

    # The callback for when a PUBLISH message is received from the server.
    def on_message(self, client, user_data, msg):
        """

        :param client:
        :param user_data:
        :param msg: msg.topic is the topic of the message
        msg.payload is the payload of the message
        :return: None
        """
        pass
