# features/promotions.feature
Feature: Promotions Admin UI
  As an eCommerce manager
  I want to manage promotions through a web interface
  So that I can create, update, and track promotional campaigns

  Scenario: Load the admin UI page
    When I visit the "Home Page"
    Then I should see "Promotions Manager" in the title

  Scenario: Create a promotion from the UI
    When I visit the "Home Page"
    And I click "Create"
    And I fill the create form with:
      | Name        | Promotion Type | Value | Product ID | Start Date | End Date   |
      | Winter Sale | PERCENT        | 50    | 9999       | 2030-11-12 | 2030-11-30 |
    And I submit the create form
    Then I should see the promotions table updated with "Winter Sale"

  Scenario: Delete a promotion from the UI
    Given the following promotions
      | Name        | Promotion Type | Value | Product ID | Start Date | End Date   |
      | Summer Sale | PERCENT        | 20    | 2001       | 2030-06-01 | 2030-08-31 |
    When I visit the "Home Page"
    Then I should see the promotions table updated with "Summer Sale"
    When I click the delete button for "Summer Sale"
    Then I should see the delete confirmation modal
    When I confirm the deletion
    Then I should not see "Summer Sale" in the promotions table

  Scenario: Edit a promotion from the UI
    Given the following promotions
      | Name       | Promotion Type | Value | Product ID | Start Date | End Date   |
      | Flash Sale | DISCOUNT       | 100   | 3001       | 2030-01-01 | 2030-01-31 |
    When I visit the "Home Page"
    Then I should see the promotions table updated with "Flash Sale"
    When I click the edit button for "Flash Sale"
    Then I should see the edit modal
    When I fill the edit form with:
      | Name               | Promotion Type | Value | Product ID | Start Date | End Date   |
      | Flash Sale Updated | PERCENT        | 25    | 3002       | 2030-02-01 | 2030-02-28 |
    And I submit the edit form
    Then I should see the promotions table updated with "Flash Sale Updated"

  Scenario: Deactivate a promotion from the UI
    Given the following promotions
      | Name        | Promotion Type | Value | Product ID | Start Date | End Date   |
      | Spring Sale | PERCENT        | 15    | 4001       | 2030-03-01 | 2030-03-31 |
    When I visit the "Home Page"
    Then I should see the promotions table updated with "Spring Sale"
    When I click the deactivate button for "Spring Sale"
    Then I should see the deactivate confirmation modal
    When I confirm the deactivation
    Then the end date for "Spring Sale" should be yesterday in the promotions table

  Scenario: Filter promotions by Active status
    Given the following promotions
      | Name         | Promotion Type | Value | Product ID | Start Date | End Date   |
      | Active Sale  | PERCENT        | 20    | 5001       | 2024-01-01 | 2026-12-31 |
      | Expired Sale | PERCENT        | 30    | 5002       | 2020-01-01 | 2020-12-31 |
    When I visit the "Home Page"
    And I click the "Active" filter pill
    Then I should see the promotions table updated with "Active Sale"
    And I should not see "Expired Sale" in the promotions table
    And the URL should contain "active=true"

  Scenario: Filter promotions by Inactive status
    Given the following promotions
      | Name         | Promotion Type | Value | Product ID | Start Date | End Date   |
      | Active Sale  | PERCENT        | 20    | 6001       | 2024-01-01 | 2026-12-31 |
      | Expired Sale | PERCENT        | 30    | 6002       | 2020-01-01 | 2020-12-31 |
    When I visit the "Home Page"
    And I click the "Inactive" filter pill
    Then I should see the promotions table updated with "Expired Sale"
    And I should not see "Active Sale" in the promotions table
    And the URL should contain "active=false"

  Scenario: Search promotions by name
    Given the following promotions
      | Name        | Promotion Type | Value | Product ID | Start Date | End Date   |
      | Summer Sale | PERCENT        | 25    | 7001       | 2030-06-01 | 2030-08-31 |
      | Winter Sale | PERCENT        | 30    | 7002       | 2030-12-01 | 2030-12-31 |
    When I visit the "Home Page"
    And I search for "Summer Sale"
    Then I should see the promotions table updated with "Summer Sale"
    And I should not see "Winter Sale" in the promotions table
    And the URL should contain "name=Summer+Sale"

  Scenario: Filter promotions by Type
    Given the following promotions
      | Name          | Promotion Type | Value | Product ID | Start Date | End Date   |
      | Percent Sale  | PERCENT        | 20    | 8001       | 2030-01-01 | 2030-12-31 |
      | Discount Sale | DISCOUNT       | 100   | 8002       | 2030-01-01 | 2030-12-31 |
    When I visit the "Home Page"
    And I select "DISCOUNT" in the Type filter
    Then I should see the promotions table updated with "Discount Sale"
    And I should not see "Percent Sale" in the promotions table
    And the URL should contain "promotion_type=DISCOUNT"

  Scenario: Filter promotions by Product ID
    Given the following promotions
      | Name   | Promotion Type | Value | Product ID | Start Date | End Date   |
      | Sale A | PERCENT        | 20    | 9001       | 2030-01-01 | 2030-12-31 |
      | Sale B | PERCENT        | 30    | 9002       | 2030-01-01 | 2030-12-31 |
    When I visit the "Home Page"
    And I filter by product ID "9001"
    Then I should see the promotions table updated with "Sale A"
    And I should not see "Sale B" in the promotions table
    And the URL should contain "product_id=9001"

  Scenario: Clear all filters
    Given the following promotions
      | Name        | Promotion Type | Value | Product ID | Start Date | End Date   |
      | Summer Sale | PERCENT        | 25    | 1001       | 2030-06-01 | 2030-08-31 |
    When I visit the "Home Page"
    And I click the "Active" filter pill
    Then the URL should contain "active=true"
    When I click the Clear filters button
    Then the URL should not contain parameters
    And I should see the promotions table updated with "Summer Sale"
