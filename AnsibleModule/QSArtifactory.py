from ansible.module_utils.basic import *
import json
import re
import requests


class Artifactory():

    def __init__(self, build_id, artifactory_ip, artifactory_username, artifactory_password, file_name, artifact_repo                                                                                                                        , xray_ip='', xray_username='', xray_password=''):

        self.build_id = build_id
        self.artifactory_ip = artifactory_ip
        self.artifactory_username = artifactory_username
        self.artifactory_password = artifactory_password
        self.artifact_repo = artifact_repo
        self.file_name = file_name
        self.xray_ip = xray_ip
        self.xray_username = xray_username
        self.xray_password = xray_password

        if self.xray_ip and self.xray_username and xray_password:
            self.xray = True
        else:
            self.xray = False

    def workflow(self):
        if self.artifactory_ip == 'AUTO':
            try:
                fn = '/tmp/%s.err' % self.file_name
                #raise Exception(fn)
                with open(fn, 'r') as f:
                    s = f.read()
            except:
                return 'Skipping deployment with unfilled Artifactory info'
            raise Exception(s)
        status, text = self._download_artifact()
        if status >= 400:
            out = self._get_failed_reason(text)
            with open('/tmp/%s.err' % self.file_name, 'w') as f:
                f.write(out)
            raise Exception(out)
        return 'Downloaded ' + self.file_name

    def _download_artifact(self):
        # Should run locally on the App
        artifact_url = 'http://{art_ip}:8081/artifactory/{repo}/{build}/{file}'.format(art_ip=self.artifactory_ip, re                                                                                                                        po=self.artifact_repo, build=self.build_id, file=self.file_name)
        commands = [
            'curl',
            '-v',
            '-u%s:%s' % (self.artifactory_username, self.artifactory_password),
            '--stderr', '-',
            '-o', '/tmp/' + self.file_name,
             artifact_url
        ]
        p = subprocess.Popen(commands, stdout=subprocess.PIPE)
        output, err = p.communicate()
        m = re.search(r'< HTTP/\S+ (\d+) (.*)', output)
        if m:
            code, text = m.groups()
            code = int(code)
            return code, text
        else:
            url = 'http://{artifact_url}:8081/artifactory/webapp/#/artifacts/browse/tree/General/{repo}/{build}/{file                                                                                                                        }'.format(artifact_url=self.artifactory_ip, repo=self.artifact_repo, build=self.build_id, file=self.file_name)
            msg = "Error downloading the artifact. Error: {}\nOutput: {}\nCheck URL: {}".format(err, output, url)
            # raise Exception(msg)
            return 500, msg

    def _get_failed_reason(self, text):

        artifact_url = 'http://{art_url}:8081/artifactory/api/storage/{repo}/{build}/{file}'.format(art_url=self.arti                                                                                                                        factory_ip, repo=self.artifact_repo, build=self.build_id, file=self.file_name)

        csj = json.loads(requests.get(artifact_url, auth=(self.artifactory_username, self.artifactory_password)).text                                                                                                                        )
        if 'checksums' not in csj or 'sha1' not in csj['checksums']:
            msg = "Failure downloading artifact from '{artifact_url}': {error}\nThe build id '{build_id}' may be inva                                                                                                                        lid.".format(artifact_url=artifact_url, error=text, build_id=self.build_id)
            return msg
        checksum = csj['checksums']['sha1']

        if not self.xray:
            msg = "Xray not provided, cannot check for blocking reason"
            return msg

        xray_url = 'http://{xray_ip}:8000/api/v1/summary/artifact'.format(xray_ip=self.xray_ip)
        r = requests.post(xray_url,
                          data='{"checksums":["%s"]}' % checksum,
                          headers={'Content-Type': 'application/json'},
                          auth=(self.artifactory_username, self.artifactory_password))
        if r.status_code >= 400:
            msg = 'Deployment of artifact id {build} failed; Check Xray: {xray_error}'.format(build=self.build_id, xr                                                                                                                        ay_error=r.text)
            return msg
        oreason = json.loads(r.text)
        reason = ''
        already = set()
        for artifact in oreason['artifacts']:
            if artifact['general']['name'] in already:
                continue
            already.add(artifact['general']['name'])
            for issue in artifact['issues']:
                reason += 'JFrog Xray: %s %s issue raised %s by provider %s: %s: %s\n' % (
                    issue['severity'],
                    issue['issue_type'].lower(),
                    issue['created'],
                    issue['provider'],
                    issue['summary'],
                    issue['description'])

        url = 'http://{artifact_url}:8081/artifactory/webapp/#/artifacts/browse/tree/General/{repo}/{build}/{file}'.f                                                                                                                        ormat(
            artifact_url=self.artifactory_ip, repo=self.artifact_repo, build=self.build_id, file=self.file_name)
        msg = "JFrog Xray found issue: {}\nCheck URL: {}".format(reason, url)

        return 'Deployment of artifact id {} failed: {}'.format(self.build_id, msg)


def main():

    fields = {
        "build_id": {"required": True, "type": "str"},
        "artifactory_ip": {"required": True, "type": "str"},
        "artifactory_username": {"required": True, "type": "str"},
        "artifactory_password": {"required": True, "type": "str"},
        "file_name": {"required": True, "type": "str"},
        "artifact_repo": {"required": True, "type": "str"},
        "xray_ip": {"required": False, "type": "str"},
        "xray_username": {"required": False, "type": "str"},
        "xray_password": {"required": False, "type": "str"},
    }

    module = AnsibleModule(argument_spec=fields)

    build_id = module.params['build_id']
    artifactory_ip = module.params['artifactory_ip']
    artifactory_username = module.params['artifactory_username']
    artifactory_password = module.params['artifactory_password']
    file_name = module.params['file_name']
    artifact_repo = module.params['artifact_repo']
    xray_ip = module.params['xray_ip']
    xray_username = module.params['xray_username']
    xray_password = module.params['xray_password']

    out = {}
    try:
        art = Artifactory(build_id, artifactory_ip, artifactory_username, artifactory_password, file_name, artifact_r                                                                                                                        epo, xray_ip, xray_username, xray_password)
        result = art.workflow()
        out['Success'] = 'Artifactory operations complete: {}'.format(result)
    except Exception, e:
        out['Failed'] = 'Encountered an error: {}'.format(e)
        module.fail_json(msg=str(out))

    module.exit_json(changed=True, meta=out)

if __name__ == '__main__':
    main()
