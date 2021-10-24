## Setup
use python 3.9  
all needed lib is writed in requirements.txt file  
to install libs: ```run pip install -r requirements.txt ```  
Must use proxy to solve blocked problem when we send too many request at same time. use [ProxyPool](https://github.com/Python3WebSpider/ProxyPool/tree/master/proxypool) to get free proxy
## Overview
We split it into 2 tasks:  
1. get all questions id  
2. get detail of question from question id. the detail contains answers and replies. If you already has question id you only need to run task 2  

To start crawler you run the main.py file.  
If you don't pass any argument it will run full task( 1st and 2nd).  
If you want to run 1st task only. the command is like ```main.py --step1 true```    
If you want to run 2nd task only. the command is like ```main.py --step2 true```

## Output:
### Default output is saved in ```/storage``` directory  
The directory structure is:
```
    /storage  
        html #raw html content  
        output #question's detail info in json format that we get in 2nd task  
        temp  
            question_stock #all question id that we get in 1st task. if we already get detail of all question in file then we'll append "done" postfix into filename
```
### Change output dir:
pass expected dir as argument when init ```FILE_STORAGE_CONFIG``` that defined in line 119 of ```utils.py``` file  
example: ```FILE_STORAGE_CONFIG = StorageConfig("/expected_dir")```

I already created systemd service for auto start when server started. its name is ```chiebukuro```. You can start it by running ```sudo systemclt start chiebukuro```

Example of running in no hang up mode:   
```
    nohup /home/azureuser/chiebukuro_crawler/env/bin/python main.py --step2 true > cmd.log.txt
```


## Customize
### Proxy  
To use other proxy you must override `ProxyManager` class in `utils.py` file  
If you want send direct request insteading via proxy. change default value of `use_proxy` params at line 77 in `utils.py` to **False**

### Concurrent process  
In default the parallel process is equal with server's cpu core. To edit parallel process number you can edit `CPU_CORES`'s value in `chiebukuro.py`  
In one process we has 10 cocurrent asynchronous tasks. In `chiebukuro.py` file you can edit `max_concurrent_task` variable's value to number you want  
It means that we are running 32*10=320 tasks concurrently 