view: airports {
  sql_table_name: `cloud-training-demos.looker_flights.airports` ;;

  dimension: id {
    primary_key: yes
    type: number
    hidden: yes
    value_format_name: decimal_0
    sql: ${TABLE}.id ;;
  }

  dimension_group: active {
    hidden: yes       # not working as of 2021-02-16
    description: "Date this airport became active; if no data, then January 1970"
    type: time
    timeframes: [month, month_num, year]
    convert_tz: no
    sql: --CASE WHEN ${TABLE}.act_date = '' THEN '1970-01-01'
          --else
          timestamp(date(cast(split(${TABLE}.act_date,"/")[offset(1)] as int64)
                    , cast(split(${TABLE}.act_date,"/")[offset(0)] as int64)
                    , 01)
                    )
          --END
          ;;
  }

  dimension: act_date {   # values are like '01/1903', '12/2000'
    hidden: yes
    type: string
    sql: ${TABLE}.act_date ;;
  }

  dimension: city {
    type: string
    sql: ${TABLE}.city ;;
  }

  dimension: cntl_twr {
    hidden: yes
    type: string
    sql: ${TABLE}.cntl_twr ;;
  }

  dimension: control_tower {
    type: yesno
    sql: ${TABLE}.cntl_twr = TRUE ;;
  }

  dimension: code {
    type: string
    sql: rtrim(${TABLE}.code) ;;
  }

  dimension: county {
    type: string
    sql: ${TABLE}.county ;;
  }

  dimension: elevation {
    hidden: yes
    type: number
    value_format_name: decimal_0
    sql: ${TABLE}.elevation ;;
  }

  dimension: facility_type {
    type: string
    sql: ${TABLE}.fac_type ;;
  }

  dimension: full_name {
    type: string
    sql: ${TABLE}.full_name ;;
  }

  dimension: joint_use {
    type: yesno
    sql: ${TABLE}.joint_use = "Y" ;;
  }

  dimension: latitude {
    type: number
    sql: ${TABLE}.latitude ;;
  }

  dimension: longitude {
    type: number
    sql: ${TABLE}.longitude ;;
  }

  dimension: map_location {
    type: location
    sql_latitude: ${latitude} ;;
    sql_longitude: ${longitude} ;;
  }

  dimension: is_major {
    type: yesno
    sql: ${TABLE}.major = TRUE ;;
  }

  dimension: state {
    type: string
    map_layer_name: us_states
    sql: ${TABLE}.state ;;
  }

  measure: count {
    type: count
    drill_fields: [id, full_name]
  }

  measure: min_elevation {
    type: min
    sql: ${elevation} ;;
  }

  measure: max_elevation {
    type: max
    sql: ${elevation} ;;
  }

  measure: average_elevation {
    type: average
    sql: ${elevation} ;;
  }

  measure: with_control_tower_count {
    type: count
    filters: {
        field: control_tower
        value: "Yes"
    }
  }
}
