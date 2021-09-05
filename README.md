## Keyvault client

The keyvault client will

* Retrieve a list of paramstore values in the target account
* Search parameters names.
* Retrieve paramater values


### Requirements

**For the binary:**

Set the file as executable and run.

**For the Python script:**

Python 3 and a few modules are needed. Assuming you already have python3 and pip3 on your system do the following:

```
sudo pip3 install urwid pyperclip
```




### Passing credentials

ps-client uses AWS cli credentials.

A profile can be passed with the `--profile` switch

If no profile is passed it will attempt to automatically dectet credentials.

https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html

### Usage

`--profile` pass a aws credentail file profile 



`ps-client`

`ps-client --profile dev`
