# SSH

To enter into the hidden `ssh` folder 
```bash
cd ~/.ssh 
```

### Connecting
Connect to external machine
```bash
ssh -i ~/.ssh/<my_key.pem> <cloud_machine_name>@<public IP adress>
```

You can also modify the configuration so to make this easier

```bash
nano ~/.ssh/config
```

and write a command

```
Host <command>
  HostName <public IP adress>
  User <cloud name machine>
  IdentityFile ~/.ssh/<your_key>.pem
  StrictHostKeyChecking no
```

So then you can just run

```bash
ssh <command>
```