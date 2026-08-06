connection: "bigquery_public_data_looker"

explore: fruit_basket {}

view: fruit_basket {
  derived_table: {
    sql: select  'apple' as fruit_type,  'red' as color,  'yes' as is_round,  1.25 as price_per_pound,  0.6 as weight,  0.75 as price  union all
        select  'banana' as fruit_type,  'yellow' as color,  'no' as is_round,  0.75 as price_per_pound,  0.7 as weight,  0.53 as price  union all
        select  'lemon' as fruit_type,  'yellow' as color,  'no' as is_round,  2.25 as price_per_pound,  0.22 as weight,  0.5 as price  union all
        select  'apple' as fruit_type,  'red' as color,  'yes' as is_round,  1.25 as price_per_pound,  0.55 as weight,  0.69 as price  union all
        select  'lime' as fruit_type,  'green' as color,  'no' as is_round,  2.4 as price_per_pound,  0.18 as weight,  0.43 as price  union all
        select  'lime' as fruit_type,  'green' as color,  'no' as is_round,  2.4 as price_per_pound,  0.17 as weight,  0.41 as price  union all
        select  'apple' as fruit_type,  'green' as color,  'yes' as is_round,  1.15 as price_per_pound,  0.4 as weight,  0.46 as price  union all
        select  'orange' as fruit_type,  'orange' as color,  'yes' as is_round,  1.45 as price_per_pound,  0.45 as weight,  0.65 as price  union all
        select  'banana' as fruit_type,  'yellow' as color,  'no' as is_round,  0.75 as price_per_pound,  0.75 as weight,  0.56 as price  union all
        select  'lemon' as fruit_type,  'yellow' as color,  'no' as is_round,  2.25 as price_per_pound,  0.2 as weight,  0.45 as price  union all
        select  'orange' as fruit_type,  'orange' as color,  'yes' as is_round,  1.45 as price_per_pound,  0.5 as weight,  0.73 as price  union all
        select  'lemon' as fruit_type,  'yellow' as color,  'no' as is_round,  2.25 as price_per_pound,  0.19 as weight,  0.43 as price
        ;;
  }

  dimension: fruit_type {
    type: string
    sql: ${TABLE}.fruit_type ;;
  }

  dimension: color {
    type: string
    sql: ${TABLE}.color ;;
  }

  dimension: is_round {
    type: string
    sql: ${TABLE}.is_round ;;
  }

  dimension: price_per_pound {
    type: number
    sql: ${TABLE}.price_per_pound ;;
  }

  dimension: weight {
    type: number
    sql: ${TABLE}.weight ;;
  }

  dimension: price {
    type: number
    sql: ${TABLE}.price ;;
  }

  measure: count {
    type: count
  }

  measure: average_weight {
    type: average
    value_format_name: decimal_2
    sql: ${weight} ;;
  }

  measure: average_price {
    type: average
    value_format_name: usd
    sql: ${price} ;;
  }

  measure: total_weight {
    type: sum
    value_format_name: decimal_2
    sql: ${weight} ;;
  }

  measure: total_price {
    type: sum
    value_format_name: usd
    sql: ${price} ;;
  }

  measure: average_price_per_pound{
    type: average
    value_format_name: usd
    sql: ${price_per_pound} ;;
  }

  measure: count_types {
    type: count_distinct
    sql: ${fruit_type} ;;
  }

  measure: count_color {
    type: count_distinct
    sql: ${color} ;;
  }

}
