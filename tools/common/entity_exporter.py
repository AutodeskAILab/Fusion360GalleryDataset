import data_util
import adsk.core
from collections import OrderedDict


class BaseExporter:
    """Base Data extructure to export information of fusion entities"""

    def __init__(self, entity, custom_uuid=None):
        self.entity = entity
        self.name = self.entity.name
        self.data = OrderedDict()
        if custom_uuid is None:
            data_util.set_uuid(self.entity)
        else:
            data_util.set_custom_uuid(self.entity, custom_uuid)
        self.uuid = data_util.get_uuid(self.entity)

    def get_data(self):
        return (self.data, None)


class BodyExporter(BaseExporter):
    def __init__(self, entity, custom_uuid=None):
        super().__init__(entity, custom_uuid)

    def get_data(self):
        """Populate the data structure and return it"""
        try:
            self.data["name"] = self.name
            self.data["type"] = data_util.get_object_type(self.entity)
            self.data["smt"] = f"{self.uuid}.smt"
            self.data["step"] = f"{self.uuid}.stp"
            return (self.data, None)

        except Exception as ex:
            # We catch any exceptions that we throw here and return the error
            # without any data, meaning we log and skip export
            error = f"Error getting data for {self.name}: {str(ex)}"
            return (None, error)


class BodyExporterCollection:
    def __init__(self, entity):
        """ Suitable for occurrences and components"""
        self.entity = entity

    def get_body_exporters(self):
        body_exporter_collection = []
        for body in self.entity.bRepBodies:
            body_exporter = BodyExporter(body)
            body_exporter_collection.append(body_exporter)
        return body_exporter_collection


class ComponentExporter(BaseExporter):
    def __init__(self, entity, custom_uuid=None):
        super().__init__(entity, custom_uuid)
        self.body_exporter_collection = BodyExporterCollection(entity)

    def get_data(self, is_root=False):
        """Populate the data structure and return it"""
        try:
            self.data["name"] = "root" if is_root else self.name
            self.data["type"] = data_util.get_object_type(self.entity)
            body_exporters = self.body_exporter_collection.get_body_exporters()
            bodies_ids = list(
                map(lambda body_ex: body_ex.uuid, body_exporters))
            self.data["bodies"] = bodies_ids
            return (self.data, None)

        except Exception as ex:
            # We catch any exceptions that we throw here and return the error
            # without any data, meaning we log and skip export
            error = f"Error getting data for {self.name}: {str(ex)}"
            return (None, error)


class OccurrenceExporter(BaseExporter):
    def __init__(self, entity, custom_uuid=None):
        super().__init__(entity, custom_uuid)
        self.body_exporter_collection = BodyExporterCollection(
            entity.component)

    def get_data(self):
        """Populate the data structure and return it"""
        try:
            self.data["name"] = self.name
            self.data["type"] = data_util.get_object_type(self.entity)
            self.data["component"] = self.get_component_id()
            self.data["transform"] = data_util.get_matrix3d_coordinate_system(
                self.entity.transform)
            self.data["is_visible"] = self.entity.isLightBulbOn
            # self.entity.transform = transform
            self.data["occurrences"] = self.get_occurrences_data()
            self.data["bodies"] = {}
            body_exporters = self.body_exporter_collection.get_body_exporters()
            for body_exp in body_exporters:
                self.data["bodies"][body_exp.uuid] = {
                    "is_visible": body_exp.entity.isLightBulbOn
                }
            return (self.data, None)

        except Exception as ex:
            # We catch any exceptions that we throw here and return the error
            # without any data, meaning we log and skip export
            error = f"Error getting data for {self.name}: {str(ex)}"
            return (None, error)

    def get_component_id(self):
        """get uuid from attributes, set it if not exists"""
        component = self.entity.component
        id = data_util.get_uuid(component)
        if id is None:
            data_util.set_uuid(component)
            id = data_util.get_uuid(component)
        return id

    def get_occurrences_data(self):
        """Get occurrences data base on Occurrence Exporter"""
        data = {}
        for occ in self.entity.childOccurrences:
            occ_exporter = OccurrenceExporter(occ)
            occ_data, error = occ_exporter.get_data()
            if error is None:
                data[occ_exporter.uuid] = occ_data
        return data
