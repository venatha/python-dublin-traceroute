from __future__ import absolute_import
from __future__ import print_function

import copy
import datetime

import tabulate


class TracerouteResults(dict):

    def __init__(self, json_results):
        dict.__init__(self, json_results)
        self._flattened = None

    def flatten(self, rebuild=False):
        '''
        Flatten the traceroute JSON data and return them as a list of {k: v}
        rows. NOTE: the flattened object is cached, and it can be modified by
        other code. If you need an independent copy, call with rebuild=True .
        '''
        if not rebuild and self._flattened is not None:
            return self._flattened

        rows = []
        results = copy.deepcopy(self)
        for port, flow in results['flows'].items():
            for packet in flow:

                sent = packet['sent']

                packet['sent_timestamp'] = sent['timestamp']
                for k, v in sent['ip'].items():
                    packet['sent_ip_{k}'.format(k=k)] = v
                for k, v in sent['udp'].items():
                    packet['sent_udp_{k}'.format(k=k)] = v

                received = packet['received']
                if received:
                    packet['received_timestamp'] = received['timestamp']
                    try:
                        for k, v in received['ip'].items():
                            packet['received_ip_{k}'.format(k=k)] = v
                    except KeyError:
                        pass
                    try:
                        for k, v in received['icmp'].items():
                            packet['received_icmp_{k}'.format(k=k)] = v
                    except KeyError:
                        pass

                rows.append(packet)
        self._flattened = rows
        return rows

    def to_dataframe(self):
        '''
        Convert traceroute results to a Pandas DataFrame.
        '''
        # pandas is imported late because it does not compile yet on PyPy
        import pandas
        return pandas.DataFrame(self.flatten())

    def pretty_print(self):
        '''
        Print the traceroute results in a tabular form.
        '''
        # tabulate is imported here so it's not a requirement at module load
        headers = ['ttl'] + list(self['flows'].keys())
        columns = []
        max_hops = 0
        for flow_id, hops in self['flows'].items():
            column = []
            for hop in hops:
                try:
                    if hop['received']['ip']['src'] != hop['name']:
                        name = '\n' + hop['name']
                    else:
                        name = hop['received']['ip']['src']
                    column.append('{name} ({rtt} usec)'.format(
                        name=name,
                        rtt=hop['rtt_usec'])
                    )
                except TypeError:
                    column.append('*')
                if hop['is_last']:
                    break
            max_hops = max(max_hops, len(column))
            columns.append(column)
        columns = [range(1, max_hops + 1)] + columns
        rows = zip(*columns)
        print(tabulate.tabulate(rows, headers=headers))

    def stats(self):
        df = self.to_dataframe()
        start_ts = df.sent_timestamp.astype(float).min()
        start_time = datetime.datetime.fromtimestamp(start_ts)
        end_ts = df.received_timestamp.astype(float).max()
        end_time = datetime.datetime.fromtimestamp(end_ts)
        total_time = end_time - start_time
        max_ttl = df[df.is_last == True].sent_ip_ttl.dropna().max()
        print(
            'Start time      : {st}\n'
            'End time        : {et}\n'
            'Total time      : {tt}\n'
            'Max TTL reached : {mttl}\n'
            .format(
                st=start_time,
                et=end_time,
                tt=total_time,
                mttl=max_ttl,
             ))
