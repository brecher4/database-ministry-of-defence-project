import os, shelve, csv
from typing import Any, Dict, List, Type
import db_api


class DBField(db_api.DBField):
    def __init__(self, name, type):
        self.name = name
        self.type = type


class SelectionCriteria(db_api.SelectionCriteria):
    def __init__(self, field_name, operator, value):
        self.field_name = field_name
        self.operator = operator
        self.value = value


class DBTable(db_api.DBTable):  
    def __init__(self, name, fields, key_field_name):
        self.name = name
        self.fields = fields
        self.key_field_name = key_field_name
        self.path_file = os.path.join('db_files', self.name + '.db')
        self.indexes = []

        # create shelve file
        s = shelve.open(self.path_file)
        self.num_record = len(s.keys())
        s.close()

    
    def get_names_fields(self):
        return [field.name for field in self.fields]


    def get_format_index_file(self, field_name):
        return os.path.join('db_files', 'index_' + field_name + '_' + self.name + '.db')


    def count(self) -> int:
        return self.num_record


    def insert_record(self, values: Dict[str, Any]) -> None:
        if self.key_field_name not in values.keys():
            raise ValueError("The key is missing")

        s = shelve.open(self.path_file)

        if str(values[self.key_field_name]) in s.keys():
            s.close()
            raise ValueError("The key must be unique")
 
        self.fields += [ DBField(item, Any) for item in values.keys() if item not in self.get_names_fields()]       
        s[str(values[self.key_field_name])] = values
        self.num_record += 1
        s.close()
        

    def delete_record(self, key: Any) -> None:
        s = shelve.open(self.path_file, writeback=True)

        if str(key) not in s.keys():
            s.close()
            raise ValueError("The key doesn't exist")
 
        s.pop(str(key))
        self.num_record -= 1
        s.close()


    def are_criterias_met(self, record: Dict[str, Any], criterias: List[SelectionCriteria]):
        for criteria in criterias:
            if criteria.field_name in record.keys():
                if criteria.operator == '=':
                    criteria.operator = "=="
                try:
                    is_criteria_met = eval(f'{record[criteria.field_name]} {criteria.operator} {criteria.value}')
                
                except NameError:

                    is_criteria_met = eval(f'str(record[criteria.field_name]) {criteria.operator} str(criteria.value)')
                
                if not is_criteria_met:
                    return False
        
        return True


    def delete_records(self, criteria: List[SelectionCriteria]) -> None:
        s = shelve.open(self.path_file, writeback=True)
        
        # using hash index by key
        for item in criteria:
            if item.field_name == self.key_field_name and item.operator == '=':
                record = s[str(item.value)]

                if self.are_criterias_met(record, criteria):
                    s.pop(str(item.value))
                    self.num_record -= 1
                    s.close()
                    return

        for record in s.values():
            if self.are_criterias_met(record, criteria):
                s.pop(str(record[self.key_field_name]))
                self.num_record -= 1
        
        s.close()


    def get_record(self, key: Any) -> Dict[str, Any]:
        s = shelve.open(self.path_file)
        record = s.get(str(key), None)
        s.close()
        return record


    def update_record(self, key: Any, values: Dict[str, Any]) -> None:
        s = shelve.open(self.path_file, writeback=True)
        
        if str(key) not in s.keys():
            s.close()
            raise ValueError("The key doesn't exist")
        
        self.fields += [ DBField(item, Any) for item in values.keys() if item not in self.get_names_fields()]
        s[str(key)].update(values)
        s.close()


    def query_table(self, criteria: List[SelectionCriteria]) -> List[Dict[str, Any]]:
        s = shelve.open(self.path_file)

        list_match_records = []
        
        # using hash index by key
        for item in criteria:
            if item.field_name == self.key_field_name and item.operator == '=':
                record = s[str(item.value)]

                if self.are_criterias_met(record, criteria):
                    s.close()
                    return [record]

        for record in s.values():
            if self.are_criterias_met(record, criteria):
                list_match_records += [record]
        
        s.close()
        return list_match_records


###############
    def create_index(self, field_to_index: str) -> None:
        if field_to_index not in self.get_names_fields():
            raise ValueError("Field index doesn't exist in table's fields")


class DataBase(db_api.DataBase):
    def __init__(self):
        self.db_tables = {}
        self.num_tables_in_DB = 0
        self.reload_from_disk()
        

    def reload_from_disk(self):
        with open('database.csv', 'r') as csv_file:
            csv_reader = csv.reader(csv_file)

            for row in csv_reader:
                table_name = row[0]
                self.db_tables[table_name] = DBTable(table_name, row[1], row[2])
                self.num_tables_in_DB += 1


    def create_table(self, table_name: str, fields: List[DBField], key_field_name: str) -> DBTable:
        if table_name in self.db_tables.keys():
            raise ValueError("The table name exists in the database")

        if key_field_name not in [field.name for field in fields]:
            raise ValueError("The key doesn't exist in fields list")
        
        self.db_tables[table_name] = DBTable(table_name, fields, key_field_name)
        self.num_tables_in_DB += 1

        with open('database.csv', "a", newline='') as csv_file:
            csv_writer = csv.writer(csv_file)
            data_table = [table_name, fields, key_field_name]
            csv_writer.writerow(data_table)

        return self.db_tables[table_name]


    def num_tables(self) -> int:
        return self.num_tables_in_DB


    def get_table(self, table_name: str) -> DBTable:
        if table_name not in self.db_tables.keys():
            raise ValueError("The table name doesn't exist in the database")

        return self.db_tables.get(table_name, None)


    def delete_selve_file(self, table_name):
        s = (os.path.join('db_files', table_name + ".db.bak"))
        os.remove(s)
        s = (os.path.join('db_files', table_name + ".db.dat"))
        os.remove(s)
        s = (os.path.join('db_files', table_name + ".db.dir"))
        os.remove(s)


    def delete_table(self, table_name: str) -> None:
        if table_name not in self.db_tables.keys():
            raise ValueError("The table name doesn't exist in the database")
        
        self.num_tables_in_DB -= 1
        self.delete_selve_file(table_name)
        self.db_tables.pop(table_name)
        
        # remove the table from database.csv
        with open('database.csv','r') as csv_file:
            csv_reader = csv.reader(csv_file)
            lines = []
            for row in csv_reader:
                lines += [row]
            
        with open('database.csv','w',newline='') as csv_file:
            csv_writer = csv.writer(csv_file) 
            for line in lines:
                if line[0] != table_name:
                    csv_writer.writerow(line)
        

    def get_tables_names(self) -> List[Any]:
        return list(self.db_tables.keys())

##############
    def query_multiple_tables(
            self,
            tables: List[str],
            fields_and_values_list: List[List[SelectionCriteria]],
            fields_to_join_by: List[str]
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError
