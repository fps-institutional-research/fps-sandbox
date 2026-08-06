test: flights_explore {
  explore_source: flights {
    column: code { field: carriers.code }
    column: state { field: aircraft_origin.state }
    column: state { field: aircraft_destination.state }
    column: count {}
    filters: {
      field: carriers.code
      value: "WN"
    }
  }
  assert: flights_has_data {
    expression: ${flights.count} > 0 ;;
  }
  assert: carriers_and_aircraft_have_data {
    expression: count(${aircraft_origin.state}) = 388 ;;
  }
  assert: aircraft_self_join_works {
    expression: count(${aircraft_destination.state}) = 388 ;;
  }
}
