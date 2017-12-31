@Echo off
chcp 65001

:Start
py -3.6 Bird.py
timeout 3
git fetch
goto Start
