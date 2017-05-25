from cloudshell.api.cloudshell_api import AppConfiguration, ConfigParams, ConfigParam
from cloudshell.helpers.scripts import cloudshell_scripts_helpers as helpers
from cloudshell.helpers.scripts import cloudshell_dev_helpers


ARTIFACROTY_APP_MODELS = ['ArtApp']
ARTIFACTORY_MODEL = 'Artifactory'
XRAY_MODEL = 'Xray'


class artifactory_helper():

    def __init__(self):
        self.api = helpers.get_api_session()
        self.res_id = helpers.get_reservation_context_details().id
        self.reservation_detilas =  self.api.GetReservationDetails(self.res_id).ReservationDescription
        self.api.WriteMessageToReservationOutput(self.res_id, "Artifactory Helper")

    def execute(self):
        art_apps = self._find_artifactory_resources()
        if not art_apps:
            print "No Artifactory Apps"
            return
        art_ip, art_user, art_pass = self._get_resource_info(ARTIFACTORY_MODEL)
        x_ip, x_user, x_pass = self._get_resource_info(XRAY_MODEL)
        build = self._get_build_id()
        p1 = ConfigParam('ArtifactoryIP', art_ip)
        p2 = ConfigParam('ArtifactoryUsername', art_user)
        p3 = ConfigParam('ArtifactoryPassword', art_pass)
        p4 = ConfigParam('XrayIP', x_ip)
        p5 = ConfigParam('XrayUsername', x_user)
        p6 = ConfigParam('XrayPassword', x_pass)
        p7 = ConfigParam('BuildID', build)

        for app in art_apps:

            app_conf1 = AppConfiguration(app.Name, [p1, p2, p3, p4, p5, p5, p6, p7])

            try:
                configuration_result = self.api.ConfigureApps(reservationId=self.res_id,
                                                              appConfigurations=[app_conf1]) #, app_conf2, app_conf3, app_conf4, app_conf5, app_conf6, app_conf7])

                if not configuration_result.ResultItems:
                    self.api.WriteMessageToReservationOutput(reservationId=self.res_id, message='No Artifactory apps to configure')
                    return

                failed_apps = []
                for conf_res in configuration_result.ResultItems:
                    if conf_res.Success:
                        message = "App '{0}' configured successfully".format(conf_res.AppName)
                        self.api.WriteMessageToReservationOutput(reservationId=self.res_id,
                                                                 message=message)

                    else:
                        message = "App '{0}' configuration failed due to {1}".format(conf_res.AppName,
                                                                                     conf_res.Error)

                        self.api.WriteMessageToReservationOutput(reservationId=self.res_id,
                                                                 message=message)
                        failed_apps.append(conf_res.AppName)

                if not failed_apps:
                    self.api.WriteMessageToReservationOutput(reservationId=self.res_id, message=
                    'Apps were configured successfully.')
                else:
                    self.api.WriteMessageToReservationOutput(reservationId=self.res_id, message=
                    'Apps: {0} configuration failed. See logs for more details'.format(
                        ",".join(failed_apps)))
                    raise Exception("Configuration of apps failed see logs.")
            except Exception as ex:

                raise

    def _find_artifactory_resources(self):
        resources = []
        for resource in self.reservation_detilas.Resources:
            for app_model in ARTIFACROTY_APP_MODELS:
                if app_model == resource.ResourceModelName:
                    resources.append(resource)

        return resources

    def _get_build_id(self):
        res_name = self.reservation_detilas.Name
        if '-' not in res_name:
            raise Exception('Reservation name should end with "-" and the build id')
        build_id = res_name.split('-', 1)[1].strip()
        return build_id

    def _get_resource_info(self, resource_model):
        resources = self.api.FindResources(resourceModel=resource_model, showAllDomains=False)
        if not resources:
            resources = self.api.FindResources(resourceModel=resource_model, showAllDomains=True)
            if not resources:
                raise Exception("Unable to find Resource with Model: '{}'".format(resource_model))

        for resource in resources.Resources:
            username, password, ip = '', '', ''
            self.api.WriteMessageToReservationOutput(self.res_id, resource.Name)
            attributes = self.api.GetResourceDetails(resource.FullName, True).ResourceAttributes
            for attribute in attributes:
                if attribute.Name == 'User':
                    username = attribute.Value
                elif attribute.Name == 'Password':
                    password = self.api.DecryptPassword(attribute.Value).Value
            if username and password:
                ip = resource.Address
                self.api.WriteMessageToReservationOutput(self.res_id, ip)
                return ip, username, password
        else:
            raise Exception("No Resource found with matching attributes")



# cloudshell_dev_helpers.attach_to_cloudshell_as('admin', 'admin', 'Global', '060c92f0-e5d6-4845-92a1-7021d5c8fde7', '192.168.85.41')
#
# artifactory_helper().execute()