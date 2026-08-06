# Apache Beam Data Pipeline

This script was developed using best practices for Apache Beam.

## Best Practices
- Authentication: Use Setup() in your DoFn to fetch the token once per worker, not once per element.
- Rate Limiting: Use a Reshuffle or GroupIntoBatches before the API call to control parallelism.
- Secrets: Never hardcode Client IDs. Use PipelineOptions or a Secret Manager (like Google Secret Manager) and access it during Setup().
- Connectivity: Use apache_beam.io.requestresponse (available in newer Beam versions) to handle retries and backoff automatically.
- Graceful Handling: If it's normal for some records to not exist in the SKY API, modify your __call__ method in Caller_Local.py to return None or an empty object instead of raising an exception.
- Dead Letter Queue: Instead of failing the pipeline, you can catch the error and output the failed record to a separate PCollection (a "Dead Letter Queue") for later inspection. Wrap your API call in a try/except block. Use yield to output successful responses to the main output. Use yield tagged_output to send errors to an error PCollection.


        ###### Blackbaud SKY API Education Management "School" endpoints
        #### Documentation: https://developer.sky.blackbaud.com/api#api=school
        #### Rate Limit: 10 calls per second
        #### Quota: 25,000 calls per 24-hour period