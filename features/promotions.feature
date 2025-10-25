# features/promotions.feature
Feature: Promotions Admin UI bootstrap
  As a service administrator
  I want a working BDD harness that drives the UI only
  So that I can validate the service behavior from the outside-in

  Background:
    Given the Promotions UI is available

  Scenario: UI smoke (open /ui and see the title)
    Then the page title contains "Promotions Admin"
