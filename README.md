# MLOps Level

1) `No Automation`: Essentially jupyter notebooks, no experiment tracking, no model, no model registry

2) `DevOps but no MLOps`: There is some level of automation, like automated releases, unit tests, CI/CD, operational metrics. No ML specific automation.

3) `Automated Training`: As thte title says, there is a training pipeline, an experiment tracking so you now which model is in production, there is a model registry.

4) `Automated Deployment`: No human to deploy a model. There is an ML Platform to deploy models. We might have A/B tests so that automatically the ML Platform decides which model is better.Models are monitored at this stage.

5) `Full MLOps operations`: Everything is automated. Model monitoring is automated and triggers new training and new deployment.

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

With this config then it is easy to use VSCode with the remote extensions to connect to the cloud server.