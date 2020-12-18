# Running test suite    

1 find pod name with `docker ps | grep myorg_controller`, it will be the last value the returned line. ('myorg_myorg-controller_1' by default)

2 Open interactive terminal in pod with `docker exec -it myorg_myorg-controller_1 bash` 

3 `pwd` should show 'home/indy/' and `ls` should show the contents of  _/issuer_controller_ folder.

4 run `pytest` to get test results.