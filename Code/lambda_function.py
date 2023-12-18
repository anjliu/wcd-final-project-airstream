import boto3
import time
import json
import re
import csv
### Copyright 2022, Simplemaps.com, https://simplemaps.com, Released under MIT license - https://opensource.org/licenses/MIT ### 

# build athena query
def query_athena(params):
      
  def athena_to_s3(session, params, max_execution = 20):
      
      # execute query
      def single_query(client, params):
        QueryString = params["query"]
        QueryExecutionContext = {'Database': params['database']}  
        ResultConfiguration = {'OutputLocation': 's3://' + params['bucket'] +'/' + params['path']}
        print('Output Location: '+ResultConfiguration['OutputLocation'])
        response = client.start_query_execution(QueryString=QueryString, QueryExecutionContext=QueryExecutionContext, ResultConfiguration=ResultConfiguration)
        return response

      # define query specs
      client = session.client('athena', region_name=params["region"])
      execution = single_query(client, params)
      execution_id = execution['QueryExecutionId']
      state = 'RUNNING'

      # try to execute query and catch errors
      while (max_execution > 0 and state in ['RUNNING', 'QUEUED']):
          max_execution = max_execution - 1
          response = client.get_query_execution(QueryExecutionId = execution_id)
          if 'QueryExecution' in response and \
                  'Status' in response['QueryExecution'] and \
                  'State' in response['QueryExecution']['Status']:
              state = response['QueryExecution']['Status']['State']
              if state == 'FAILED':
                  error_reason = response['QueryExecution']['Status']['StateChangeReason']
                  return False
              elif state == 'SUCCEEDED':
                  s3_path = response['QueryExecution']['ResultConfiguration']['OutputLocation']
                  filename = re.findall('.*\/(.*)', s3_path)[0]
                  return filename
          time.sleep(1)     
      return False    
      
  def cleanup(session, params): #deletes all files in path
      s3 = session.resource('s3')
      my_bucket = s3.Bucket(params['bucket'])
      for item in my_bucket.objects.filter(Prefix=params['path']):
          item.delete()    

  # connection to S3 bucket
  session = boto3.Session()
  filename = athena_to_s3(session, params)
  key =  '{path}{filename}'.format(path=params['path'], filename=filename)
  s3 = session.resource('s3')    
  obj = s3.Object(params['bucket'], key).get()
  obj_lines = [x.decode("utf-8") for x in obj["Body"].iter_lines()]
  cleanup(session, params)    
  output = [x for x in csv.DictReader(obj_lines)]
  return output

# if the user provides a custom query in the url, retrieve that query
def get_query_from_url(params, event): #formulate query from url
    url_parameters = event.get('queryStringParameters')
    query = params['query'] 
    if url_parameters:
      url_query, field, value, operator = url_parameters.get('query'), url_parameters.get('field'), url_parameters.get('value'), url_parameters.get('operator', '=')
      field2, value2, operator2 = url_parameters.get('field2'), url_parameters.get('value2'), url_parameters.get('operator2', '=')
      limit = url_parameters.get('limit', '10')
      orderby = url_parameters.get('orderby', '')
      orderby = ' order by {}'.format(orderby) if orderby else ''
      if url_query:
        query = url_parameters.get('query')
      # add to the query the specified parameters
      elif field and value:
        if field2 and value2:
          query = "select * from {} where {}{}'{}' and {}{}'{}'{} limit {};".format(params['table'], field, operator, value, field2, operator2, value2, orderby, limit)
        else:
          query = "select * from {} where {}{}'{}'{} limit {};".format(params['table'], field, operator, value, orderby, limit)
      
      #convert any string values into numbers
      pattern = r"(.*)([<>]=?)'([\d\.]*)'(.*)"
      replacement = r"\1\2\3\4"
      query = re.sub(pattern, replacement, query)
      query = re.sub(pattern, replacement, query)
         
    return query

def lambda_handler(event, context):
 
    # define system parameters
    params = {
        "region": "us-east-2",
        "database": "air_stream_db",
        "table": "air_stream",
        "bucket": "air-stream",
        "path": "url_query_results/",
        # default query, gets the latest record for each flight, if it's within the last 3 minutes of the latest record
        "query": 'select from_unixtime(updated) as time_updated,lat,lng,flight_iata,dir from air_stream a1 where (a1.flight_iata,a1.updated) in (select a.flight_iata, max(updated) from air_stream a group by a.flight_iata) and updated > (select max(updated) from air_stream) - 3*60;'
    }
    
    params['query'] = get_query_from_url(params, event)

    output = query_athena(params)

    return {
        'statusCode': 200,
        'body':json.dumps(output, ensure_ascii=False)  
    }