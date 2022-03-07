import json
import requests
import time
import os
import traceback
import urllib3
urllib3.disable_warnings()

#def get_env_variables():
#    vm_name = os.environ['VMNAME']
#    dep_name = os.environ['DEPNAME']
#    return vm_name, dep_name
refresh_token = os.environ['REFRESH_TOKEN']
proj_id = os.environ['PROJECT_ID']

#vm_name, dep_name = get_env_variables()
#vm_name = ['fd-amer-000037', 'fd-amer-000038']
dep_name = 'MOAD_Migration_01'
api_url_base = 'https://api.mgmt.cloud.vmware.com/'
headers = {'Content-Type': 'application/json'}


def get_access_key():
    api_url = 'https://console.cloud.vmware.com/csp/gateway/am/api/auth/api-tokens/authorize?refresh_token={0}'.format(refresh_token)
    response = requests.post(api_url, headers=headers, verify=False)
    if response.status_code == 200:
        json_data = json.loads(response.content.decode('utf-8'))
        key = json_data['access_token']
        return key
    else:
        print(response.status_code)

access_key = get_access_key()
headers1 = {'Content-Type': 'application/json',
           'Authorization': 'Bearer {0}'.format(access_key)}

def get_deployment_name(dep_name):
        api_url = '{0}/deployment/api/deployments'.format(api_url_base)
        response = requests.get(api_url, headers=headers1, verify=False)
        if response.status_code == 200:
            json_data = json.loads(response.content.decode('utf-8'))
            n = 0
            n2 = json_data['numberOfElements']
            while True:
                name = json_data['content'][n]['name']
                if name == dep_name:
                    print ("Found Deployment")
                    id = json_data['content'][n]['id']
                    full_link = "/deployment/api/deployments/" + id
                    deploymentID = id
                    return deploymentID
                    break
                else:
                    if n >= n2:
                        print("Did Not Find Deployment")
                        break
                    else:
                        n = n + 1
        else:
            return response.status_code

def get_deployment_resources(deploymentID):
        api_url = '{0}deployment/api/deployments/{1}/resources'.format(api_url_base,deploymentID)
        response = requests.get(api_url, headers=headers1, verify=False)
        if response.status_code == 200:
            json_data = json.loads(response.content.decode('utf-8'))
            n = 0
            n2 = (int(json_data['numberOfElements']) - 1)
            name = []
            while True:
                resourceType = json_data['content'][n]['type']
                if resourceType == "Cloud.Machine":
                    org_string = json_data['content'][n]['properties']['resourceName']
                    size = len(org_string)
                    mod_string = org_string[:size - 14]
                    name.append(mod_string)
                    #name.append(json_data['content'][n]['properties']['resourceName'])
                if n == n2:
                    vm_name = name
                    return vm_name
                    break
                else:
                    n = n + 1
        else:
            return response.status_code

def delete_deployment(deploymentID):
        api_url = '{0}deployment/api/deployments/{1}'.format(api_url_base,deploymentID)
        response = requests.delete(api_url, headers=headers1, verify=False)
        if response.status_code == 200:
            json_data = json.loads(response.content.decode('utf-8'))    
            print(json_data)
            print("Delete Original Deployment")
        else:
            return response.status_code

def extract_values(obj, key):
    """Pull all values of specified key from nested JSON."""
    arr = []
    def extract(obj, arr, key):
        """Recursively search for values of key in JSON tree."""
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, (dict, list)):
                    extract(v, arr, key)
                elif k == key:
                    arr.append(v)
        elif isinstance(obj, list):
            for item in obj:
                extract(item, arr, key)
        return arr
    results = extract(obj, arr, key)
    return results

def get_aws_cz():
    api_url = '{0}iaas/api/cloud-accounts-vmc'.format(api_url_base)
    response = requests.get(api_url, headers=headers1, verify=False)
    if response.status_code == 200:
        json_data = json.loads(response.content.decode('utf-8'))
        doc_num = json_data['numberOfElements']
        n = 0
        if doc_num > 1:
            while True:
                name = json_data['content'][n]['name']
                if name == 'VMC AWS':
                    ca_id = json_data['content'][n]['id']
                    return ca_id
                    break
                else:
                    n = n + 1
        else:
            name = json_data['content'][0]['name']
            ca_id = json_data['content'][0]['id']
            return ca_id

def get_projectId():
    api_url = '{0}iaas/api/projects'.format(api_url_base)
    response = requests.get(api_url, headers=headers1, verify=False)
    if response.status_code == 200:
        json_data = json.loads(response.content.decode('utf-8'))
        proj_id = extract_values(json_data,'id')
        proj_id = proj_id[0]
        return proj_id
    else:
        return None

def create_onboard_plan():
    #proj_id = get_projectId()
    aws_cz_id = get_aws_cz()
    api_url = '{0}relocation/onboarding/plan'.format(api_url_base)
    data =  {
                "name": "Onboard-OVH-Resource",
                "projectId": proj_id,
                "endpointIds": [
                    aws_cz_id
                ]
            }
    response = requests.post(api_url, headers=headers1, data=json.dumps(data), verify=False)
    if response.status_code == 200:
        json_data = json.loads(response.content.decode('utf-8'))
        link = json_data['documentSelfLink']
        print('Successfully Created Onboard Plan')
        return link
    else:
        return None

def get_compute_link(plan_link,vm_name):
        api_url = '{0}relocation/api/wo/query-unmanaged-machine'.format(api_url_base)
        data =  {
                  "planLink": plan_link,
                  "expandFields": [
                    "documentSelfLink",
                    "name"
                  ],
                  "filters": [
                    {
                    "field": "NAME",
                    "values": [
                        vm_name
                    ]
                    }
                ],
                  "optionExcludePlanMachines": "true"
                }
        response = requests.post(api_url, headers=headers1, data=json.dumps(data), verify=False)
        if response.status_code == 200:
            json_data = json.loads(response.content.decode('utf-8'))
            print(json_data)
            res_link = extract_values(json_data,'documentSelfLink')
            for x in res_link:
                api_url2 = '{0}provisioning/uerp{1}'.format(api_url_base,x)
                response2 = requests.get(api_url2, headers=headers1, verify=False)
                if response2.status_code == 200:
                    json_data = json.loads(response2.content.decode('utf-8'))
                    vmname = json_data['name']
                    if vmname == vm_name:
                        return x

def get_deployment_link(dep_name):
        api_url = '{0}/deployment/api/deployments'.format(api_url_base)
        response = requests.get(api_url, headers=headers1, verify=False)
        if response.status_code == 200:
            json_data = json.loads(response.content.decode('utf-8'))
            n = 0
            n2 = json_data['numberOfElements']
            while True:
                name = json_data['content'][n]['name']
                if name == dep_name:
                    print ("Found Deployment")
                    id = json_data['content'][n]['id']
                    full_link = "/deployment/api/deployments/" + id
                    return full_link
                    break
                else:
                    if n >= n2:
                        print("Did Not Find Deployment")
                        break
                    else:
                        n = n + 1
        else:
            return response.status_code

def create_onboard_deployment(plan_link,dep_name):
   #deployment_link = get_deployment_link(dep_name)
    api_url = '{0}relocation/onboarding/deployment'.format(api_url_base)
    data =  {
              "planLink": plan_link,
              "name": dep_name,
              "description": "Migrated"
            }
    response = requests.post(api_url, headers=headers1, data=json.dumps(data), verify=False)
    print(dep_name)
    print(plan_link)
    if response.status_code == 200:
        json_data = json.loads(response.content.decode('utf-8'))
        print('Successfully Created Onboard Deployment')
        link = json_data['documentSelfLink']
        return link
    else:
        return response.status_code

def add_resource_to_plan(plan_link,compute_link,vm_name,deploy_link):
    api_url = '{0}relocation/onboarding/task/create-deployment-bulk'.format(api_url_base)
    data =  {
              "deployments": [
                {
                  "resources": [
                    {
                      "link": compute_link,
                      "name": vm_name
                    }
                  ],
                  "deploymentLink": deploy_link
                }
              ],
              "planLink": plan_link
            }
    response = requests.post(api_url, headers=headers1, data=json.dumps(data), verify=False)
    if response.status_code == 200:
        print('Successfully Added Resource to Onboard Plan')
    else:
        return None

def get_dep_link(plan_link):
        api_url = '{0}relocation/onboarding/deployment?expand&$filter=((planLink%20eq%20%27{1}%27))'.format(api_url_base,plan_link)
        response = requests.get(api_url, headers=headers1, verify=False)
        if response.status_code == 200:
            json_data = json.loads(response.content.decode('utf-8'))
            planlink = json_data['documentLinks']
            planlink = planlink[0]
            return planlink
        else:
            return None

def rename_plan_deployment(dep_link,vm_name,plan_link):
    dep_link = dep_link[1:]
    api_url = '{0}{1}'.format(api_url_base,dep_link)
    data =  {
              "planLink": plan_link,
              "name": vm_name,
              "bpAutoGenerate": "false"
            }
    response = requests.patch(api_url, headers=headers1, data=json.dumps(data), verify=False)
    if response.status_code == 200:
        print('Successfully Renamed Plan Deployment')
    else:
        return None

def run_plan(plan_link):
    api_url = '{0}relocation/api/wo/execute-plan'.format(api_url_base)
    data =  {
              "planLink": plan_link
            }
    response = requests.post(api_url, headers=headers1, data=json.dumps(data), verify=False)
    if response.status_code == 200:
        print('Successfully Ran OnBoard Plan')
    else:
        return None

def delete_plan(plan_link):
    plan_link = plan_link[1:]
    api_url = '{0}{1}'.format(api_url_base,plan_link)
    response = requests.delete(api_url, headers=headers1, verify=False)
    if response.status_code == 200:
        print('Successfully Deleted OnBoard Plan')
    else:
        return None

print('Getting Resources from old Deployment and removing it to re-onboard')
deploymentID = get_deployment_name(dep_name)
vm_name = get_deployment_resources(deploymentID)
print(vm_name)

print('Onboarding Resource From Migration')
plan_link = create_onboard_plan()
deploy_link = create_onboard_deployment(plan_link,dep_name)

for i in range(len(vm_name)):
    while True:
        status = get_compute_link(plan_link,vm_name[i])
        if status != None:
            compute_link = status
            print("Found Resource")
            break
    #deploy_link = create_onboard_deployment(plan_link,dep_name)
    add_resource_to_plan(plan_link,compute_link,vm_name[i],deploy_link)

print('Deleting original deployment')
delete_deployment(deploymentID)
time.sleep(300)

print('Running Plan')
run_plan(plan_link)
time.sleep(60)

print('Deleting Plan')
delete_plan(plan_link)
