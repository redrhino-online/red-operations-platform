"""Behavioral tests for the stage 10 funnel forecast (Measurement domain).

Rules under test come from SPEC.md section 4, stage 10 (the engagement measures
qualified traffic, leads, appointments and sales and then improves) and Phase 5
("metric registry... observations and experiment records"), shaped by the canon's
advertising forecast equation (canon file 22: the Metrics Matrix "solves the
funnel unit economics before real data exists"; canon file 23: annual customer
value, close rate, booking rate, cost per lead, return on ad spend):

- The forecast equation is the canon's: a lead is worth the annual customer value
  times the show rate, close rate and lead-to-booking rate; a strategy session is
  worth the annual customer value times the close rate; a scenario's return on ad
  spend is the booked revenue divided by the ad spend.
- Every input is a typed, registered, versioned, same-tenant metric figure
  carrying its basis, so a forecast cannot be built from free-text numbers.
- Placeholder inputs are explicitly planned-not-observed: a forecast over any
  placeholder input is labelled PLACEHOLDER, and a placeholder figure never
  counts as an observed measurement.
- A forecast is a projection, never an observed result: it cannot be projected to
  an OBSERVATION claim (SPEC.md section 3, Measurement invariant).
"""

import unittest
from dataclasses import FrozenInstanceError

from redops.contexts.measurement.domain.errors import (
    FunnelForecastObservationError,
    FunnelMetricRoleError,
    FunnelTenantBoundaryError,
    InvalidFunnelFigureError,
    InvalidFunnelForecastError,
)
from redops.contexts.measurement.domain.value_objects import (
    FunnelForecast,
    FunnelMetricRole,
    MeasurementBasis,
    funnel_figure,
)

from .fixtures import (
    funnel_economics,
    funnel_figure as figure,
    funnel_forecast,
    funnel_metric,
    measurement_record,
    placeholder_record,
)


class FunnelFigureTests(unittest.TestCase):
    def test_a_valid_figure_keeps_its_role_basis_and_value(self):
        fig = figure(FunnelMetricRole.LEAD_BOOKING_RATE)

        self.assertIs(FunnelMetricRole.LEAD_BOOKING_RATE, fig.role)
        self.assertEqual(5.0, fig.value)
        self.assertIs(MeasurementBasis.OBSERVED, fig.basis)
        self.assertEqual(0.05, fig.fraction)

    def test_a_percent_figure_exposes_its_fraction(self):
        fig = figure(FunnelMetricRole.SESSION_CLOSE_RATE, value=25.0)

        self.assertEqual(0.25, fig.fraction)

    def test_a_figure_requires_identity_value_and_source(self):
        for field in ("source",):
            with self.subTest(field=field):
                with self.assertRaises(InvalidFunnelFigureError):
                    figure(FunnelMetricRole.LEAD_BOOKING_RATE, **{field: "  "})

    def test_a_percent_figure_must_be_a_percentage_between_zero_and_hundred(self):
        for value in (-1.0, 101.0):
            with self.subTest(value=value):
                with self.assertRaises(InvalidFunnelFigureError):
                    figure(FunnelMetricRole.LEAD_BOOKING_RATE, value=value)

    def test_a_currency_figure_must_be_a_non_negative_number(self):
        with self.assertRaises(InvalidFunnelFigureError):
            figure(FunnelMetricRole.ANNUAL_CUSTOMER_VALUE, value=-1.0)
        with self.assertRaises(InvalidFunnelFigureError):
            figure(FunnelMetricRole.ANNUAL_CUSTOMER_VALUE, value="lots")

    def test_a_figure_requires_a_registered_metric_of_its_role(self):
        with self.assertRaises(FunnelMetricRoleError):
            figure(
                FunnelMetricRole.LEAD_BOOKING_RATE,
                metric=funnel_metric(FunnelMetricRole.SESSION_CLOSE_RATE),
            )

    def test_a_figure_is_immutable(self):
        fig = figure(FunnelMetricRole.LEAD_BOOKING_RATE)

        with self.assertRaises(FrozenInstanceError):
            fig.value = 0.0


class FunnelFigureProjectionTests(unittest.TestCase):
    def test_uses_the_newest_observed_record_for_the_metric(self):
        older = measurement_record(
            metric=funnel_metric(FunnelMetricRole.LEAD_BOOKING_RATE),
            record_id="measure-a",
            value=4.0,
        )
        newer = measurement_record(
            metric=funnel_metric(FunnelMetricRole.LEAD_BOOKING_RATE),
            record_id="measure-b",
            value=6.0,
        )

        fig = funnel_figure(
            role=FunnelMetricRole.LEAD_BOOKING_RATE,
            metric=funnel_metric(FunnelMetricRole.LEAD_BOOKING_RATE),
            records=[older, newer],
            placeholder_value=5.0,
            placeholder_source="plan://funnel-forecast",
        )

        self.assertIs(MeasurementBasis.OBSERVED, fig.basis)
        self.assertEqual(6.0, fig.value)
        self.assertEqual("analytics://campaign-report", fig.source)

    def test_falls_back_to_an_explicit_placeholder_without_an_observation(self):
        fig = funnel_figure(
            role=FunnelMetricRole.LEAD_BOOKING_RATE,
            metric=funnel_metric(FunnelMetricRole.LEAD_BOOKING_RATE),
            records=[placeholder_record(
                metric=funnel_metric(FunnelMetricRole.LEAD_BOOKING_RATE)
            )],
            placeholder_value=5.0,
            placeholder_source="plan://funnel-forecast",
        )

        self.assertIs(MeasurementBasis.PLACEHOLDER, fig.basis)
        self.assertEqual(5.0, fig.value)
        self.assertEqual("plan://funnel-forecast", fig.source)

    def test_ignores_another_tenants_records(self):
        foreign_metric = funnel_metric(
            FunnelMetricRole.LEAD_BOOKING_RATE, tenant_id="other-client"
        )
        foreign = measurement_record(
            metric=foreign_metric, tenant_id="other-client", value=99.0
        )

        fig = funnel_figure(
            role=FunnelMetricRole.LEAD_BOOKING_RATE,
            metric=funnel_metric(FunnelMetricRole.LEAD_BOOKING_RATE),
            records=[foreign],
            placeholder_value=5.0,
            placeholder_source="plan://funnel-forecast",
        )

        self.assertIs(MeasurementBasis.PLACEHOLDER, fig.basis)
        self.assertEqual(5.0, fig.value)


class FunnelEconomicsTests(unittest.TestCase):
    def test_the_canon_value_chain_holds(self):
        economics = funnel_economics()

        self.assertEqual(2500.0, economics.strategy_session_value)
        self.assertEqual(125.0, economics.lead_value)

    def test_target_cost_per_lead_uses_the_target_return_on_ad_spend(self):
        economics = funnel_economics()

        self.assertEqual(12.5, economics.target_cost_per_lead(
            target_return_on_ad_spend=10.0
        ))

    def test_a_show_rate_below_hundred_percent_discounts_the_lead_value(self):
        economics = funnel_economics(
            session_show_rate=figure(
                FunnelMetricRole.SESSION_SHOW_RATE, value=80.0
            )
        )

        self.assertEqual(100.0, economics.lead_value)

    def test_the_economics_requires_all_four_canon_inputs(self):
        for field in (
            "annual_customer_value",
            "lead_booking_rate",
            "session_show_rate",
            "session_close_rate",
        ):
            with self.subTest(field=field):
                with self.assertRaises(InvalidFunnelFigureError):
                    funnel_economics(**{field: "not a figure"})

    def test_every_input_must_belong_to_the_economics_tenant(self):
        with self.assertRaises(FunnelTenantBoundaryError):
            funnel_economics(
                lead_booking_rate=figure(
                    FunnelMetricRole.LEAD_BOOKING_RATE,
                    metric=funnel_metric(
                        FunnelMetricRole.LEAD_BOOKING_RATE,
                        tenant_id="other-client",
                    ),
                )
            )

    def test_the_economics_requires_a_tenant(self):
        with self.assertRaises(InvalidFunnelFigureError):
            funnel_economics(tenant_id="  ")

    def test_a_target_return_on_ad_spend_must_be_positive(self):
        with self.assertRaises(InvalidFunnelForecastError):
            funnel_economics().target_cost_per_lead(
                target_return_on_ad_spend=0.0
            )

    def test_the_economics_is_immutable(self):
        economics = funnel_economics()

        with self.assertRaises(FrozenInstanceError):
            economics.tenant_id = "other"

    def test_the_economics_reports_its_least_certain_input_basis(self):
        economics = funnel_economics(
            lead_booking_rate=figure(
                FunnelMetricRole.LEAD_BOOKING_RATE,
                basis=MeasurementBasis.PLACEHOLDER,
            )
        )

        self.assertIs(MeasurementBasis.PLACEHOLDER, economics.input_basis)


class FunnelForecastTests(unittest.TestCase):
    def test_the_forecast_equation_holds(self):
        forecast = funnel_forecast(ad_spend=5000.0, cost_per_lead=5.0)

        self.assertEqual(1000.0, forecast.leads)
        self.assertEqual(50.0, forecast.booked_sessions)
        self.assertEqual(50.0, forecast.shown_sessions)
        self.assertEqual(12.5, forecast.customers)
        self.assertEqual(125000.0, forecast.revenue)
        self.assertEqual(25.0, forecast.return_on_ad_spend)

    def test_the_forecast_is_a_projection_never_an_observation(self):
        forecast = funnel_forecast()

        self.assertTrue(forecast.is_forecast)
        with self.assertRaises(FunnelForecastObservationError):
            forecast.as_observation(claim_id="claim-forecast")

    def test_a_placeholder_input_makes_the_projection_planned(self):
        forecast = funnel_forecast(
            economics=funnel_economics(
                session_close_rate=figure(
                    FunnelMetricRole.SESSION_CLOSE_RATE,
                    basis=MeasurementBasis.PLACEHOLDER,
                )
            )
        )

        self.assertIs(MeasurementBasis.PLACEHOLDER, forecast.input_basis)

    def test_the_forecast_requires_a_positive_spend_and_cost_per_lead(self):
        for spend in (0.0, -100.0):
            with self.subTest(spend=spend):
                with self.assertRaises(InvalidFunnelForecastError):
                    funnel_forecast(ad_spend=spend)
        for cost in (0.0, -1.0):
            with self.subTest(cost=cost):
                with self.assertRaises(InvalidFunnelForecastError):
                    funnel_forecast(cost_per_lead=cost)

    def test_the_forecast_must_share_its_economics_tenant(self):
        with self.assertRaises(FunnelTenantBoundaryError):
            FunnelForecast(
                tenant_id="other-client",
                economics=funnel_economics(),
                ad_spend=5000.0,
                cost_per_lead=5.0,
            )

    def test_the_forecast_is_immutable(self):
        forecast = funnel_forecast()

        with self.assertRaises(FrozenInstanceError):
            forecast.ad_spend = 1.0


if __name__ == "__main__":
    unittest.main()
