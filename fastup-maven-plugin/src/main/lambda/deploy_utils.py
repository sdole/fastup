from __future__ import print_function

import json
import os

import boto3
import datetime

import util

json.JSONEncoder.default = lambda self, obj: (obj.isoformat() if isinstance(obj, datetime.datetime) else None)

cfn_client = boto3.client('cloudformation')
s3 = boto3.client('s3')
asg_client = boto3.client('autoscaling')
ec2 = boto3.client('ec2')


# def do_instances_exist(app_instance_tag):
#     instances = ec2.describe_instances(Filters=[{'Name': 'tag-key', 'Values': [app_instance_tag]}])
#     return len(instances['Reservations'][0]['Instances']) > 0


# def do_router_exists():
#     tags = asg_client.describe_tags(Filters=[
#         {
#             "Name": "key",
#             "Values": ["tvarit:purpose"]
#         },
#         {
#             "Name": "value",
#             "Values": ["router"]
#         }
#     ])
#
#     instances = ec2.describe_instances(Filters=[{'Name': 'tag:key', 'Values': ["tvarit:purpose=router"]}])
#     print(json.dumps(instances))
#
#     return len(instances['Reservations']) > 0 and len(instances['Reservations'][0]['Instances']) > 0


# def ensure_router_auto_scaling_group_has_instances():
#     tags = asg_client.describe_tags(Filters=[
#         {
#             "Name": "key",
#             "Values": ["tvarit:purpose"]
#         },
#         {
#             "Name": "value",
#             "Values": ["router"]
#         }
#     ])
#
#     router_asg_name = tags['Tags'][0]['ResourceId']
#
#     auto_scaling_groups = asg_client.describe_auto_scaling_groups(AutoScalingGroupNames=[router_asg_name])
#     if auto_scaling_groups['AutoScalingGroups'][0]['MaxSize'] == 0:
#         asg_client.update_auto_scaling_group(AutoScalingGroupName=router_asg_name, MinSize=2, MaxSize=6)


def create_app_auto_scaling_group(war_file_info, rds_stack_name):
    '''
    Here, we know that the app auto scaling group does not exist. so, we find template url for app autoscaling group, set
    parameters on it from s3 war file metadata and execute it.
    :return:
    '''
    group_id = war_file_info["metadata"]["group-id"]
    artifact_id = war_file_info["metadata"]["artifact-id"]
    version = war_file_info["metadata"]["version"]
    app_context_root = war_file_info["metadata"]["context_root"]
    if app_context_root == "/":
        app_context_root = "ROOT"
    context_config_url = war_file_info["metadata"]["context_config_url"]
    health_check_url = war_file_info["metadata"]["health_check_url"]

    print(json.dumps(war_file_info, indent=True, sort_keys=True))

    network_resources = util.make_base_output_map_from_cfn("Network")
    iam_resources = util.make_base_output_map_from_cfn("IAM")
    rds_output_map = util.make_stack_output_map(rds_stack_name)

    availability_zones = network_resources["AvailabilityZonesOutput"]
    app_security_groups = network_resources["AppSecurityGroupOutput"]
    elb_subnets = network_resources["ElbSubnetsOutput"]
    app_subnets = network_resources["AppSubnetsOutput"]
    app_elb_security_groups = network_resources["ElbSecurityGroupOutput"]
    instance_profile = iam_resources["AppInstanceProfileOutput"]
    app_setup_role = iam_resources["AppSetupRoleOutput"].split("/")[1]
    war_file_url = util.make_s3_base_url() + "/" + war_file_info["bucket_name"] + "/" + war_file_info["key"]
    app_fqdn = war_file_info["metadata"]["app_fqdn"]
    index_of_first_dot = app_fqdn.index(".")
    domain_name = app_fqdn[index_of_first_dot + 1:] + "."
    jdbc_replacer_url = util.make_cfn_url("app/replace_jdbc_params.sh")
    app_stack_parameters = [
        {"ParameterKey": "AppSubnetsParam", "ParameterValue": app_subnets},
        {"ParameterKey": "AppInstanceProfileParam", "ParameterValue": instance_profile},
        {"ParameterKey": "AvailabilityZonesParam", "ParameterValue": availability_zones},
        {"ParameterKey": "AppSecurityGroupParam", "ParameterValue": app_security_groups},
        {"ParameterKey": "ElbSubnetsParam", "ParameterValue": elb_subnets},
        {"ParameterKey": "HealthCheckUrlParam", "ParameterValue": health_check_url},
        {"ParameterKey": "ElbSecurityGroupParam", "ParameterValue": app_elb_security_groups},
        {"ParameterKey": "ArtifactBucketNameParam", "ParameterValue": war_file_info["bucket_name"]},
        {"ParameterKey": "WarFileUrlParam", "ParameterValue": war_file_url},
        {"ParameterKey": "AppSetupRoleParam", "ParameterValue": app_setup_role},
        {"ParameterKey": "AppConfigXmlUrlParam", "ParameterValue": context_config_url},
        {"ParameterKey": "ContextRootParam", "ParameterValue": app_context_root},
        {"ParameterKey": "AppDnsNameParam", "ParameterValue": app_fqdn},
        {"ParameterKey": "DomainNameHostedZoneNameParam", "ParameterValue": domain_name},
        {"ParameterKey": "DbHostParam", "ParameterValue": rds_output_map["AppDbEndpointOutput"]},
        {"ParameterKey": "DbUsernameParam", "ParameterValue": war_file_info["metadata"]["db-username"]},
        {"ParameterKey": "DbPasswordParam", "ParameterValue": war_file_info["metadata"]["db-password"]},
        {"ParameterKey": "DbNameParam", "ParameterValue": war_file_info["metadata"]["db-name"]},
        {"ParameterKey": "JdbcSetupShParam", "ParameterValue": jdbc_replacer_url}
    ]
    cfn_client.create_stack(
        StackName=(group_id + "-" + artifact_id + "-" + version).replace(".", "-"),
        TemplateURL=util.make_cfn_url("app/app.template"),
        Parameters=app_stack_parameters
    )


def modify_router_rules():
    '''
    add the newly created application asg into the router rules.
    '''
    print("do router")




def do_deploy(rds_stack_name):
    rds_stack = cfn_client.describe_stacks(StackName=rds_stack_name)
    tags_on_rds_stack = rds_stack['Stacks'][0]['Tags']
    map_of_tags_on_rds_stack = util.make_map_from_list("Key", "Value", tags_on_rds_stack)
    app_file_object_parm = map_of_tags_on_rds_stack['app_file_object']
    bucket_name = app_file_object_parm.split("::")[0]
    key_of_deployable = app_file_object_parm.split("::")[1]
    # bucket_name = "tvarit-tvarit-tomcat-plugin-test"
    # key_of_deployable = "deployables/tvarit/tomcat-plugin-test/1.0.1-SNAPSHOT/tomcat-plugin-test-1.0.1-SNAPSHOT.war"
    # util.get_app_metadata(bucket_name)
    # bucket_name = event["Records"][0]["s3"]["bucket"]["name"]
    # key_of_deployable = event["Records"][0]["s3"]["object"]["key"]
    all_metadata = util.get_app_metadata(bucket_name, key_of_deployable)
    war_info_and_metadata = {"metadata": all_metadata['Metadata'], "bucket_name": bucket_name, "key": key_of_deployable}
    # ensure_router_auto_scaling_group_has_instances()
    print("not starting router")
    deployable_name = key_of_deployable.split("/")[1]
    deployable_version = all_metadata['Metadata']['version']
    tags = asg_client.describe_tags(Filters=[
        {
            "Name": "key",
            "Values": ["tvarit:app:version", "tvarit:app:name"]
        },
        {
            "Name": "value",
            "Values": [deployable_version, deployable_name]
        }
    ])
    if len(tags['Tags']) == 0:
        print("no asg found for " + key_of_deployable + " " + deployable_version)
        create_app_auto_scaling_group(war_info_and_metadata, rds_stack_name)
        modify_router_rules()

    else:
        # TODO
        '''
        at this point, it is known that there already is a version of the same app. The developer's
        probable intention was to replace the running code with new code for the same version. So,
        find the app template in S3, change the logical name for the launch config, save it to
        another folder named revisions within the same version name folder and then execute that
        changeset. This step might also create new dependency versions. If so, create stacks for
        all those dependencues.
        '''


