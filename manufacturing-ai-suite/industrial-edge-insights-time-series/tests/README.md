## Functional tests steps
   
1. Pre-requisite script for git clone sub modules:

    ```sh
	cd ./utils/
	./github_clone.sh
	```
   
2. Install tests dependencies
   
   ```sh
   cd ./functional/
   pip3 install -r ../requirements.txt
   ```

3. For docker related test cases, run the below commands:

   > **Note**: As a prerequisite, have docker and docker compose installed

   ```sh
   pytest -v -s --html=report.html test_docker_deployment.py
   ```

4. For helm related test cases, run the below commands:

   > **Note**: As a prerequisite, have the k8s cluster setup and helm installed

   ```sh
   pytest -v -s --html=report.html test_helm_release.py
   ```
