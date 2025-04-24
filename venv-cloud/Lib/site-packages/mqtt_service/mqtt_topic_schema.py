class MqttTopicSchema(object):
    """
    Why to use 2 different topics for request and event?
    If use the same topic, device will also receive the event sent by itself.

    """

    topic_root_name = "smart-dev"
    request_topic_name = "request"
    event_topic_name = "event"
    topic_for_device_path_pattern = "%s/%s"
    topic_root_pattern_for_dev_under_gw = "/%s/%s/%s"
    topic_root_pattern_for_gw = "/%s/%s"

    def __init__(self, parent_device_id=None):
        super(MqttTopicSchema, self).__init__()

        if parent_device_id is None:
            self.request_topic_root = self.topic_root_pattern_for_gw % (self.topic_root_name, self.request_topic_name)
            self.event_topic_root = self.topic_root_pattern_for_gw % (self.topic_root_name, self.event_topic_name)
        else:
            self.request_topic_root = self.topic_root_pattern_for_dev_under_gw % (
                self.topic_root_name,
                self.request_topic_name, parent_device_id)
            self.event_topic_root = self.topic_root_pattern_for_dev_under_gw % (
                self.topic_root_name, self.event_topic_name, parent_device_id)
            self.parent_device_id = parent_device_id

    def get_event_channel_name(self, device_id):
        return self.topic_for_device_path_pattern % (self.event_topic_root, device_id)

    def get_request_channel_name(self, device_id):
        return self.topic_for_device_path_pattern % (self.request_topic_root, device_id)

    def get_gateway_request_channel_name(self):
        return self.request_topic_root

    # noinspection PyMethodMayBeStatic
    def get_device_id_from_topic(self, topic):
        topic_paths = topic.split("/")
        return topic_paths[-1]

    def get_last_will_topic(self, device_id):
        return self.get_event_channel_name(device_id)

    def get_gw_event_channel_name(self):
        return "%s/" % self.event_topic_root

    def get_gw_event_channel_wildcard(self):
        return "%s/#" % self.event_topic_root

    def is_gateway_message(self, topic):
        msg_topic = self.get_device_id_from_topic(topic.strip("/"))
        return msg_topic == self.parent_device_id

    def get_custom_action_topic_for_gw(self, action_name):
        return "/{topic_root_name}/{action_name}/{gw_id}".format(
            topic_root_name=self.topic_root_name,
            action_name=action_name,
            gw_id=self.parent_device_id)
