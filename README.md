# LOG SCAN
Versão: 1.0
Desenvolvido por Willian Jesus
Licença: GPLv3

## Dependências

Para gravar estatistica no MongoDB
yum/dnf install python3-pymongo python3-bson

## Configuração

Criar uma pasta chamada config e colocar arquivos JSON com a extensão .conf.

Exemplo: config/zabbix_sender.conf


## Arquivo de configuração do LOG SCAN

O arquivo está no formato JSON (em forma de dicionário), então respeite as limitações do arquivo de configuração para não parar o script :)

No arquivo de configuração temos 3 chaves:
* extra
* principal
* filtro

Na chave "principal", você pode gerar itens mais genéricos para os filtros. Ela será utilizada como base para todos os filtros

### Exemplo:

Você pode criar uma chave principal que tenha a expressão "PORTA.*([0-9]{1,5})" para coletar no log analisado a expressão "PORTA" seguido de 1 até 5 digitos númericos.
PORTA 53
PORTA 161
PORTA 10050

Na chave "filtro", você pode fazer filtros da chave principal.

### Exemplo:

Você pode criar filtros da rede de origem que vem a conexão na porta 53. Assim você saberá qual é o IP de origem. Você pode escolher sempre a melhor expressão regular pro filtro.

Na chave "extra" você pode personalizar a busca de qualquer expressão regular no arquivo, sem depender do filtro principal. A desvantagem de utilizar essa chave, é que você terá que fazer expressões regulares mais completas para cada item, não será um filtro de algo que já está devidamente separado.

## Arquivos de configuração com filtros e data para o Zabbix

Os arquivos devem ser no formato JSON (em forma de dicionário), então respeite as limitações do arquivo de configuração para não parar o script :)

O arquivo de configuração para o Zabbix deve conter todos esses itens:

#### "multi_keys" - Ele pode somar os valores de várias chaves que foram definidas na chave de filtros

### Exemplo:
multi_keys : ['CHAVE1','CHAVE2','CHAVE3']

### Na prática:
multi_keys : [ 80, 443, 161 ]

#### "key" - É a chave definida nos filtros. Não é possível utilizar o "multi_keys" e a "key" na mesma configuração

### Exemplo:
key : 'CHAVE1'

### Na prática:
key : 80

#### "re_item" - É o nome do filtro definido na chave "extra".

### Exemplo:
re_item : "Nome do filtro"

### Na prática:
re_item : "clientes_rede160"


#### "zabbix_item" - É o nome do item (tipo trapper) do Zabbix. Pode ou não existir no Zabbix antes da inicialização do script.

### Exemplo:
zabbix_item : "Item no Zabbix (trapper)"

### Na prática:
zabbix_item : "cliente1_rede160" 

#### "zabbix_cliente" - É o nome do host no Zabbix. Deverá ser igual ao cadastrado na interface web.

### Exemplo:
zabbix_client : "Nome do host"

### Na prática:
zabbix_client : "Zabbix server"

#### "zabbix_item_name" - Não é obrigatório, pode ser utilizado para organização do script e poderá ser utilizado em uma implementação futura
