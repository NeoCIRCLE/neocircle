# Copyright 2014 Budapest University of Technology and Economics (BME IK)
#
# This file is part of CIRCLE Cloud.
#
# CIRCLE is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# CIRCLE is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along
# with CIRCLE.  If not, see <http://www.gnu.org/licenses/>.

from itertools import islice
from socket import gethostname
import logging
import os
import pika

logger = logging.getLogger(__name__)


class Client:

    env_config = {
        "server_address": "GRAPHITE_HOST",
        "server_port": "GRAPHITE_AMQP_PORT",
        "amqp_user": "GRAPHITE_AMQP_USER",
        "amqp_pass": "GRAPHITE_AMQP_PASSWORD",
        "amqp_queue": "GRAPHITE_AMQP_QUEUE",
        "amqp_vhost": "GRAPHITE_AMQP_VHOST",
    }

    def __init__(self):
        """
        Constructor of the client class that is responsible for handling the
        communication between the graphite server and the data source. In
        order to initialize a client you must have the following
        environmental varriables:
        - GRAPHITE_SERVER_ADDRESS:
        - GRAPHITE_SERVER_PORT:
        - GRAPHITE_AMQP_USER:
        - GRAPHITE_AMQP_PASSWORD:
        - GRAPHITE_AMQP_QUEUE:
        - GRAPHITE_AMQP_VHOST:
        Missing only one of these variables will cause the client not to work.
        """
        self.name = 'circle.%s' % gethostname()
        for var, env_var in self.env_config.items():
            value = os.getenv(env_var, "")
            if value:
                setattr(self, var, value)
            else:
                raise RuntimeError('%s environment variable missing' % env_var)

    def connect(self):
        """
        This method creates the connection to the queue of the graphite
        server using the environmental variables given in the constructor.
        """
        try:
            credentials = pika.PlainCredentials(self.amqp_user, self.amqp_pass)
            params = pika.ConnectionParameters(host=self.server_address,
                                               port=int(self.server_port),
                                               virtual_host=self.amqp_vhost,
                                               credentials=credentials)
            self.connection = pika.BlockingConnection(params)
            self.channel = self.connection.channel()
            logger.info('Connection established to %s.', self.server_address)
        except RuntimeError:
            logger.error('Cannot connect to the server. '
                         'Parameters may be wrong.')
            logger.error("An error has occured while connecting to the server")
            raise
        except:  # FIXME
            logger.error('Cannot connect to the server. There is no one '
                         'listening on the other side.')
            raise

    def disconnect(self):
        """
        Break up the connection to the graphite server. If something went
        wrong while disconnecting it simply cut the connection up.
        """
        try:
            self.channel.close()
            self.connection.close()
        except RuntimeError as e:
            logger.error('An error has occured while disconnecting. %s',
                         unicode(e))
            raise

    def _send(self, message):
        """
        Send the message given in the parameters given in the message
        parameter. This function expects that the graphite server want the
        metric name given in the message body. (This option must be enabled
        on the server. Otherwise it can't parse the data sent.)
        """
        body = "\n".join(message)
        try:
            self.channel.basic_publish(exchange=self.amqp_queue,
                                       routing_key='', body=body)
        except:
            logger.error('An error has occured while sending metrics (%dB).',
                         len(body))
            raise

    @staticmethod
    def _chunker(seq, size):
        """Yield seq in size-long chunks.
        """
        for pos in xrange(0, len(seq), size):
            yield islice(seq, pos, pos + size)

    def send(self, message):
        self.connect()
        try:
            for chunk in self._chunker(message, 100):
                self._send(chunk)
        finally:
            self.disconnect()
