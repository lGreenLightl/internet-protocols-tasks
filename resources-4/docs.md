# Caching DNS-server

### Description:

Simple caching DNS-server

### Launch examples:

First launch:

```
> python task-4.py
Record from server -> 1.0.0.127.in-addr.arpa, PTR
Record from server -> github.com, A
Record from server -> github.com, AAAA
Shut down server?[y/n] y
```

Second launch:

```
> python task-4.py
Record from cache -> 1.0.0.127.in-addr.arpa, PTR
Record from cache -> github.com, A    
Record from server -> github.com, AAAA
Shut down server?[y/n] y
```
