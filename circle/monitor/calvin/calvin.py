import requests
import os


class GraphiteHandler:

    def __init__(self):
        if os.getenv("NODE_MONITOR_SERVER") is "":
            raise RuntimeError
        self.__server_name = os.getenv("NODE_MONITOR_SERVER")
        if os.getenv("NODE_MONITOR_PORT") is "":
            raise RuntimeError
        self.__server_port = os.getenv("NODE_MONITOR_PORT")
        self.__queries = []
        self.__responses = []

    def put(self, query):
        self.__queries.append(query)

    def clean_up_queries(self):
        self.__queries = []

    def clean_up_responses(self):
        self.__responses = []

    def is_empty(self):
        return len(self.__queries) is 0

    def generate_all(self):
        """
        Regenerate the queries before sending.
        """
        for query in self.__queries:
            query.generate()

    def send(self):
        """
        Generates the corrent query for the Graphite webAPI and flush all the
        queries in the fifo.
        Important: After sending queries to the server the fifo will lost its
        content.
        """
        url_base = "http://%s:%s/render?" % (self.__server_name,
                                             self.__server_port)
        for query in self.__queries:
            response = requests.get(url_base + query.get_generated())
            if query.get_format() is "json":
                self.__responses.append(response.json())  # DICT
            else:
                self.__responses.append(response)
        self.clean_up_queries()

    def pop(self):
        """
        Pop the first query has got from the server.
        """
        try:
            return self.__responses.pop(0)  # Transform to dictionary
        except:
            raise RuntimeError


class Query:

    def __init__(self):
        """
        Query initializaion:
                default format is json dictionary
                keys: ("target <string>","datapoints <list>")
        """
        self.__target = ""
        self.__metric = ""
        self.__start = ""
        self.__end = ""
        self.__function = ""
        self.__response_format = "json"
        self.__generated = ""

    def set_target(self, target):
        """
        Hostname of the target we should get the information from.
        After the hostname you should use the domain the target is in.
        Example: "foo.foodomain.domain.com.DOMAIN" where DOMAIN is
        the root of the graphite server.
        """
        self.__target = '.'.join(target.split('.')[::-1])

    def get_target(self):
        return self.__target

    def set_metric(self, metric):
        self.__metric = metric

    def get_metric(self):
        return self.__metric

    def set_absolute_start(self, year, month, day, hour, minute):
        """
        Function for setting the time you want to get the reports from.
        """
        if (len(year) > 4 or len(year) < 2):
            raise
        self.__start = hour + ":" + minute + "_" + year + month + day

    def set_relative_start(self, value, scale):
        """
        Function for setting the time you want to get the reports from.
        """
        if (scale not in ["years",
                          "months", "days", "hours", "minutes", "seconds"]):
            raise
        self.__start = "-" + str(value) + scale

    def get_start(self):
        return self.__start

    def set_absolute_end(self, year, month, day, hour, minute):
        """
        Function for setting the time until you want to get the reports from.
        """
        if (len(year) > 4 or len(year) < 2):
            raise
        self.__end = hour + ":" + minute + "_" + year + month + day

    def set_relative_end(self, value, scale):
        """
        Function for setting the time until you want to get the reports from.
        """
        if (scale not in ["years",
                          "months", "days", "hours", "minutes", "seconds"]):
            raise
        self.__end = "-" + str(value) + scale

    def get_end(self):
        return self.__end

    def set_format(self, fmat):
        """
        Function for setting the format of the response from the server.
        Valid values: ["csv", "raw", "json"]
        """
        valid_formats = ["csv", "raw", "json"]
        if fmat not in valid_formats:
            raise
        self.__response_format = fmat

    def get_format(self):
        return self.__response_format

    def generate(self):
        """
        You must always call this function before sending the metric to the
        server for it generates the valid format that the graphite API can
        parse.
        """
        tmp = "target=" + self.__target + "." + self.__metric
        if len(self.__start) is not 0:
            tmp = tmp + "&from=" + self.__start
        if len(self.__end) is not 0:
            tmp = tmp + "&until=" + self.__end
        tmp = tmp + "&format=" + self.__response_format
        self.__generated = tmp
        return self.__generated

    def get_generated(self):
        """
        Returns the generated query string.
        Throws exception if it haven't been done yet.
        """
        if len(self.__generated) is 0:
            raise
        return self.__generated
