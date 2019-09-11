#!/usr/bin/python3
# -*- encoding: utf-8 -*-

#import pytail as tailer
from datetime import datetime, timedelta
import time
import re
import json
import os
import sys

#Zabbix Sender adaptado pro projeto
from pyzabbix import ZabbixSender, ZabbixMetric

#import threading
import multiprocessing

#Iniciar a lista com os dados
data = []

#Config file
mainconfig = 'config.json'


def files(path,extension):
    for file in os.listdir(path):
        if os.path.isfile(os.path.join(path, file)):
            if re.search(extension,file):
                yield file

def statistic(localdata):
    #Dict com todos os registros para processamento
    search = {}

    #Filtro principal, com os dados para criação dos objetos
    principal = getconfig(mainconfig,'principal')
    #Todos os filtros
    filters = getconfig(mainconfig,'filters')
    #Configurações extras
    extra = getconfig(mainconfig,'extra')
    #Configurações globais
    config = getconfig(mainconfig,'config')

    for line in localdata:
        for extras in extra:
            e = extras['name']
            t = extras['regex']
            k = extras['key']

            info = re.search(t, line)
            if info:
                if k in search:
                    #search[k]["total"] += 1
                    search[k][e] += 1
                    #break
                else:
                    search[k] = []
                    #search[k] = ({"total":1})
                    search[k] = ({e:1})
                    #break

        for pregex in principal:

            s = pregex['name']
            r = pregex['regex']

            port = re.search(r, line)
            if port:
                p = port.group(1)
                if p in search:
                    search[p]["total"] += 1
                else:
                    search[p] = []
                    search[p] = ({"total":1})
                    #search[p][0]["total"] = 1

                for fregex in filters:

                    e = fregex['name']
                    f = fregex['regex']

                    fname = re.search(f, line)
                    if fname:
                        if e in search[p]:
                            search[p][e] += 1
                        else:
                            search[p][e] = 1

    #Gravar a estatistica em um arquivo
    try:
        if config[0]['exportstatistic'] == "yes":
            sfile = config[0]['statisticpath']
            with open(sfile,"w", encoding="utf8") as outfile:
                json.dump(search, outfile, ensure_ascii=False, indent=4, sort_keys=True)
    except Exception as e:
        #print("Erro ao carregar configurações de estatistica: [%s]" %e)
        logger_error.error("Erro ao carregar configurações de estatistica: [%s]" %e, exc_info=True)
    #writestatistic('statistic.json',search)
    #Importar as configurações do DB
    dblist = getconfig(mainconfig,'mongodb')

    for dbinfo in dblist:
        if dbinfo["sendtodb"] == "yes":
            #yum/dnf install python3-pymongo python3-bson
            from pymongo import MongoClient

            delay = dbinfo["delay"]
            dburl = dbinfo["dburl"]
            dbname = dbinfo["dbname"]

            try:
                #Cliente MongoDB
                client = MongoClient(dburl,serverSelectionTimeoutMS=delay)
                #Informações sobre o servidor MongoDB
                dbserverinfo = client.server_info()
                #Se o MongoDB estiver no ar
                if dbserverinfo:
                    db = client[dbname]

                #Carregar informações de dados
                for info in search:
                    #Info é o nome do collection (se ele existir criar novo collection)
                    if info:
                        stat = db[info]
                        search[info]["date"] = datetime.now()
                        search[info]["year"] = datetime.now().strftime("%Y")
                        search[info]["month"] = datetime.now().strftime("%m")
                        search[info]["day"] = datetime.now().strftime("%d")
                        search[info]["hour"] = datetime.now().strftime("%H")
                        search[info]["minute"] = datetime.now().strftime("%M")
                        stat_id = stat.insert_one(search[info]).inserted_id

                        stat_id = stat.insert_one(search[info]).inserted_id
                #print("Informações enviadas para o DB: [%s], base [%s]" %(dburl,dbname))
                if debug == "yes": logger_debug.debug("Informações enviadas para o DB: [%s], base [%s]" %(dburl,dbname))
            except Exception as e:
                #print("Erro: [%s]" %e)
                logger_error.error("Erro: [%s]" %e, exc_info=True)
    #Processar estatistica pro Zabbix
    #Diretório com arquivos de filtros
    #dirs = os.listdir( path )
    extension = '.conf$'
    dirs = files(path,extension)

    #Zabbix Server Info
    metrics = []
    m = None

    for ffile in dirs:
        filepath=path+'/'+str(ffile)
        with open(filepath, 'r') as monitorfile:
            #print("Arquivo carregado: [%s]" %ffile)
            if debug == "yes": logger_debug.debug("Arquivo carregado: [%s]" %ffile)
            filterdata = json.load(monitorfile)

        for info in filterdata:
            try: info['multi_keys']
            except KeyError: info['multi_keys'] = None

            #Valor da Multi Keys começa com 0
            value = 0

            try:  info['key']
            except KeyError:  info['key'] = None

            if info['key']:
                key = str(info['key'])
                re_item = info['re_item']
                zabbix_item = info['zabbix_item']
                zabbix_client = info['zabbix_client']

                try: search[key]
                except KeyError: search[key] = {'total': 0}

                if search[key]:
                    try: send = search[key][re_item]
                    except: send = 0

                    #print("Sender Info: Cliente: [%s] - Item: [%s] - Value: [%s]" %(cliente,zbxitem,send))
                    if debug == "yes": logger_debug.debug('Sender Info: Cliente: [%s] - Item: [%s] - Value: [%s]' %(zabbix_client,zabbix_item,send))
                    m = ZabbixMetric(zabbix_client,zabbix_item,send)
                    metrics.append(m)

            if info['multi_keys']:
                soma = 0
                keys = info['multi_keys']
                re_item = info['re_item']
                zabbix_item = info['zabbix_item']
                zabbix_client = info['zabbix_client']

                for key in keys:
                    if debug == "yes": logger_debug.debug("Multi porta: [%s] de (%s)" %(key,keys))
                    #Só para garantir que o script vai encontrar a porta no dict
                    key = str(key)
                    try: search[key]
                    except KeyError: search[key] = None

                    if search[key]:
                        try: value = search[key][re_item]
                        except: value = 0

                        soma += value
            
                if debug == "yes": logger_debug.debug('[M]Sender Info: Cliente: [%s] - Item: [%s] - Value: [%s]' %(zabbix_client,zabbix_item,value))
                m = ZabbixMetric(zabbix_client,zabbix_item,soma)
                metrics.append(m)

    #Get Zabbix Server Info
    zabbix = getconfig(mainconfig,'zabbix')

    try: zabbix
    except KeyError: zabbix = {}

    for zbx in zabbix:
        zabbixserver = zbx['zabbixserver']
        zabbixport = zbx['zabbixport']

        try:
            if zbx['sendtozabbix'] == "yes":
                if debug == "yes": logger_debug.debug('Enviar dados ao Zabbix Server [%s:%s]' %(zabbixserver,zabbixport))
                zbx = ZabbixSender(zabbixserver)
                zbx.send(metrics)
            else:
                #print("Não enviar dados ao Zabbix")
                if debug == "yes": logger_debug.debug('Não enviar dados ao Zabbix Server [%s:%s]' %(zabbixserver,zabbixport))
        except Exception as e:
            logger_error.error("Erro: [%s]" %e, exc_info=True)

def writestatistic(configfile,data):

    with open(configfile,"w", encoding="utf8") as outfile:
        json.dump(data, outfile, ensure_ascii=False, indent=4, sort_keys=True)

def follow(thefile,stime,data):
    data = []
    #print(thefile.tell())
    #thefile.seek(0,int(seekdata))
    #thefile.seek(0,os.SEEK_CUR)
    thefile.seek(0,os.SEEK_END)
    while True:
        line = thefile.readline()
        line = re.sub('[\n]','', line)

        if not line:
            try: stop
            except NameError: stop = None

            if stop:
                break

            time.sleep(stime)
            stop='yes'
            continue
        data.append(line)
        #yield line
    #print("Linhas encontradas: [%s]" %len(data))
    if debug == "yes": logger_debug.debug('Linhas encontradas: [%s]' %len(data))
    return data
    #queue.put(data)

def getconfig(configfile,service):

    with open(configfile, "r") as jsonfile:
        data = json.load(jsonfile)

    for info in data:
        if service in info:
            #print(info[service])
            return info[service]

def processlist():

    for job in jobs:
        #print("Processo: [%s] está rodando? [%s]" %(job,job.is_alive()))
        if job.is_alive() == True:
            print("Processo: [%s] está rodando" %(job))
        else:
            jobs.remove(job)
        
if __name__ == "__main__":

    #Configurações iniciais
    config = getconfig(mainconfig,'config')
    try:
        #Tempo inicial
        stime = config[0]["sleeptime"]
        #Arquivo de log
        logfile = config[0]["logfile"]
        #logfile = config[0]["logfile"]
        #PATH com os filtros
        path = config[0]["configpath"]
    except Exception as e:
        print("Erro ao carregar configurações: [%s]" %e)

    import logging
    import logging.handlers

    #Log files
    debuglog = str(config[0]["debuglog"])
    errorlog = str(config[0]["errorlog"])
    infolog = str(config[0]["infolog"])

    #Configuração básica
    #logging.basicConfig(level=logging.DEBUG,
    #                    filemode='a',
    #                    format='%(asctime)s %(name)-8s %(levelname)-8s %(message)s',
    #                    datefmt='%m-%d-%y %H:%M',
    #                    filename=debuglog)
    #Rotacionar o log básico
    #logging.handlers.RotatingFileHandler(debuglog, maxBytes=20971520, backupCount=5)

    #Log's especificos
    logger_error = logging.getLogger('error')
    logger_error.setLevel(logging.ERROR)
    #fh = logging.FileHandler(errorlog)
    #maxBytes=20MBytes
    fh = logging.handlers.RotatingFileHandler(errorlog, maxBytes=20971520, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(name)-8s %(levelname)-8s %(message)s')
    fh.setFormatter(formatter)
    logger_error.addHandler(fh)

    logger_debug = logging.getLogger('debug')
    logger_debug.setLevel(logging.DEBUG)
    #fh = logging.FileHandler(errorlog)
    #maxBytes=20MBytes
    fh = logging.handlers.RotatingFileHandler(debuglog, maxBytes=20971520, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(name)-8s %(levelname)-8s %(message)s')
    fh.setFormatter(formatter)
    logger_debug.addHandler(fh)

    logger_info = logging.getLogger('info')
    logger_info.setLevel(logging.INFO)
    #fh = logging.FileHandler(errorlog)
    #maxBytes=20MBytes
    fh = logging.handlers.RotatingFileHandler(infolog, maxBytes=20971520, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(name)-8s %(levelname)-8s %(message)s')
    fh.setFormatter(formatter)
    logger_info.addHandler(fh)


    #Configuração inicial
    logger_debug.debug('Iniciando o monitoramento')
    logger_debug.debug('LOGS: Debug [%s] - Error: [%s]' %(debuglog,errorlog))

    current = open(logfile, "r")
    curino = os.fstat(current.fileno()).st_ino

    while True:
        try:

            #Verificar se o debug está habilitado
            try: debug = config[0]["debug"]
            except: debug = None

            if debug == "yes": logger_debug.debug('Inicio da coleta')
            #logger.info('Inicio da coleta')

            if os.stat(logfile).st_ino != curino:
                new = open(logfile, "r")
                current.close()
                current = new
                curino = os.fstat(current.fileno()).st_ino

            #Coletar resultado do follow
            result = follow(current,stime,data)

            #Aguardar o tempo de sleep
            #print("Aguardar por [5] segundos")
            #time.sleep(5)

            #Gerar estatistica com os valores coletados/filtro e envio pro Zabbix e DB/filtro principal
            #process = multiprocessing.Process(target=statistic,args=[queue.get()])
            process = multiprocessing.Process(target=statistic,args=[result])
            process.start()

            if debug == "yes": logger_debug.debug('Finalizacao coleta')
        except KeyboardInterrupt:
            logger_debug.debug('Monitoramento parado')
            sys.exit(0)
        except Exception as e:
            logger_error.error("Erro: [%s]" %e, exc_info=True)


