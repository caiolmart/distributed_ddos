import pandas as pd
from datetime import datetime, timedelta
import gc
from scapy.utils import rdpcap
from scapy.layers.inet import IP, UDP, TCP

from anubisflow import AnubisFG

pcap_num = 0
capture = rdpcap('data/raw/pcap/01-12/SAT-01-12-2018_0')

files = [
    'DrDoS_NTP.csv',
    'DrDoS_DNS.csv',
    'DrDoS_LDAP.csv',
    'DrDoS_MSSQL.csv',
    'DrDoS_NetBIOS.csv',
    'DrDoS_SNMP.csv',
    'DrDoS_SSDP.csv',
    'DrDoS_UDP.csv',
    'UDPLag.csv',
    'Syn.csv',
    'TFTP.csv',
]
afg = AnubisFG()

for filename in files:
    print(f'memory_twotup has {len(afg.memory_twotup)} flows.')
    print(f'memory_fivetup has {len(afg.memory_fivetup)} flows.')
    print(f'Reading data {filename}.')
    data = pd.read_csv(f'data/raw/csv/01-12/{filename}')
    data.columns = [x.strip() for x in data.columns]
    print(f'Data has shape {data.shape}')

    cols = [
        'Source IP',
        'Source Port',
        'Destination IP',
        'Destination Port',
        'Protocol',
        'Timestamp',
        'Flow Duration',
        'Label',
    ]
    data = data[cols]
    gc.collect()

    print('Preparing timestamps.')
    data['timestamp'] = data['Timestamp'].apply(lambda x: datetime.strptime(x, '%Y-%m-%d %H:%M:%S.%f') + timedelta(hours=4))
    data['lst_timestamp'] = data.apply(lambda x: x['timestamp'] + timedelta(microseconds=x['Flow Duration']), axis=1)

    print('Preparing flow keys.')
    data['flow_key'] = data.apply(lambda x: (x['Source IP'],
                                             x['Source Port'],
                                             x['Destination IP'],
                                             x['Destination Port'],
                                             x['Protocol']), axis=1)

    drop_cols = [
        'Source IP',
        'Source Port',
        'Destination IP',
        'Destination Port',
        'Protocol',
        'timestamp',
        'Timestamp',
        'Flow Duration',
    ]
    for col in drop_cols:
        del data[col]
    gc.collect()
    print('Sorting by lst_timestamp.')
    data.columns = [x.lower() for x in data.columns]
    data = data.sort_values('lst_timestamp')

    print('Flows done.')

    print('Reading pcap and generating features.')

    outfile = f'data/interim/flow_features_{filename}'
    f = open(outfile,'w')

    idx = 0
    idx_pcap = 0
    len_data = data.shape[0]
    len_pcap = len(capture)
    while idx < len_data:
        ts = data.iloc[idx, 1].to_pydatetime()
        key = data.iloc[idx, 2]
        label = data.iloc[idx, 0]
        if idx_pcap < len_pcap:
            packet = capture[idx_pcap]
        else:
            # Get next pcap file
            pcap_num += 1
            print(f'Reading pcap {pcap_num}')
            capture = rdpcap(f'data/raw/pcap/01-12/SAT-01-12-2018_0{pcap_num}')
            idx_pcap = 0
            packet = capture[idx_pcap]
        afg.update(packet)
        if afg.lst_timestamp >= ts:
            ftrs = afg.generate_features(key)
            f.write(f'{key};{ts};{label};')
            f.write(';'.join([str(x) for x in ftrs]))
            f.write('\n')
            idx += 1
    f.close()
    print('Done')
capture.close()
