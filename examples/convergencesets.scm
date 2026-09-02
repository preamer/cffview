(monitor/convergencesets
    (
        (frequency . 3)
        (condition . #f)
        (conv-reports
            (
                (name . "con-outlet-temp-avg")
                (old-props active? #t frequency 3 report-defs
                    (report-defs "outlet-temp-avg")
                    frequency-of
                    "iteration"
                    convergence-points
                    15
                    initial-values-to-ignore
                    20
                    iteration-at-creation-or-edit
                    0
                    stop-criterion
                    1e-05
                    stop-time-step?
                    #f
                    name
                    "con-outlet-temp-avg"
                    type
                    "report-convergence"
                )
                (previous-values-to-consider . 15)
                (initial-values-to-ignore . 20)
                (iteration-at-creation-or-edit . 159)
                (stop-criterion . 1e-05)
                (report-defs . "outlet-temp-avg")
                (print? . #f)
                (plot? . #f)
                (cov? . #f)
                (active? . #f)
                (x-label . "iteration")
                (previous-values 296.2300057049123 296.2300269862954 296.2300489761936 296.2300713610923 296.2300937529555 296.230115660594 296.2301364849944 296.2301555473315 296.2301720468944 296.2301850960932 296.2301937626325 296.2301968625516 296.2301934272609 296.2301823924998 296.2301625381177 296.230132585349)
            )
        )
        (check-for . #f)
    )
)
