from .mqtt_base_listener import MqttBaseListener


class MqttMultiTopicListener(MqttBaseListener):

    def __init__(self, server="test.mosquitto.org", listening_channel_list=None):
        super(MqttMultiTopicListener, self).__init__(server)
        if listening_channel_list is None:
            listening_channel_list = []
        self.listening_channel_list = listening_channel_list

    # The callback for when the client receives a CONNACK response from the server.
    def on_connect(self, client, user_data, flags, rc):
        print("Connected with result code " + str(rc))
        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        for channel_name in self.get_listening_channel_list():
            print("subscribed to:", channel_name)
            client.subscribe(channel_name)

    def get_listening_channel_list(self):
        return self.listening_channel_list
