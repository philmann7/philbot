# td-bot
## Not yet usable or tested.
## A framework for implementing strategies using TD Ameritrade's API.
This code makes heavy use of [tda-api](https://github.com/alexgolec/tda-api). Thanks to author Alex Golec and other contributors.

### Use info
Sensitive account info should be stored in a .env file in the root directory. The program will also generate a token.json in the root directory. Both of these should be git ignored.

The .env file should be of the form
```
account_number = "xxx" 
account_password = "xxx"  
client_id = "xxx" 
```

### -------------------------------------------
`ema.py` contains simple and useful code for calculating an exponential moving average.
