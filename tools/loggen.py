#!/usr/bin/python
# -*- coding: utf-8 -*-

import random
import datetime as dt
import ipcalc
import time

import logging
import logging.handlers

clientes=['cliente1','cliente2','cliente3']
networks=['192.168.160.0/24','192.168.161.0/24']
msg=['ERROR','OK']
portas=['22','80','443','161','21']
logout='/tmp/teste.log'

datastr='%d-%m-%Y %H:%M:%S'
net = {}

logger_info = logging.getLogger('info')
logger_info.setLevel(logging.INFO)
#fh = logging.FileHandler(errorlog)
#maxBytes=20MBytes
fh = logging.handlers.RotatingFileHandler(logout, maxBytes=20971520, backupCount=5)
#formatter = logging.Formatter('%(asctime)s %(name)-8s %(levelname)-8s %(message)s')
formatter = logging.Formatter('%(asctime)s|%(message)s')
fh.setFormatter(formatter)
logger_info.addHandler(fh)

for network in networks:
    print("Montando range de IP da rede: %s" %network)
    net[str(network)] = []
    for ips in ipcalc.Network(network):
        net[str(network)].append(ips)


while True:
    netchoice = random.choice(networks)
    clientchoice = random.choice(clientes)
    #now = dt.datetime.now()
    ipchoice = random.choice(net[netchoice])
    ipchoice2 = random.choice(net[netchoice])
    prtchoice = random.choice(portas)
    msgchoice = random.choice(msg)
    logger_info.info("Client %s|PRT %s|Source %s|Dest %s|Msg %s" %(clientchoice,prtchoice,ipchoice,ipchoice2,msgchoice))
    #print("Client %s|Source %s|Dest %s|Msg %s" %(clientchoice,ipchoice,ipchoice2,msgchoice))
    time.sleep(0.1)
    #time.sleep(2)
