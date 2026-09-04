(parameters/output-parameters
    (
        (report-definition-parameter-1
            (
                (type . report-definition-parameter)
                (name (value . "lv_avg-op") (type . string-class))
                (settings (report-defn-name . "lv_avg"))
                (units-quantity)
                (fluent-units . "")
            )
        )
        (report-definition-parameter-2
            (
                (type . report-definition-parameter)
                (name (value . "hv_avg-op") (type . string-class))
                (settings (report-defn-name . "hv_avg"))
                (units-quantity)
                (fluent-units . "")
            )
        )
        (named-expression-output-parameter-1
            (
                (type . named-expression-output-parameter)
                (name (value . "p_core") (type . string-class))
                (settings (named-expression-name . "p_core"))
                (units-quantity percentage #f)
                (fluent-units . "")
            )
        )
    )
)

(parameters/input-parameters ())
