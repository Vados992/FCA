# Executable test catalogue

107 named `unittest` methods. Several contain subcases, including all ten synthetic scenarios. Assertions define expected behavior; PASS means the test observed the intended success or rejection.

Run `python -m unittest discover -s tests -v` or `python scripts/validate.py`. The latter also replays each of the ten independent proof packets.

| Module | Test class | Assertion case |
|---|---|---|
| `test_api.py` | `APITests` | `test_liveness_without_credentials_has_no_private_data` |
| `test_api.py` | `APITests` | `test_api_requires_authentication` |
| `test_api.py` | `APITests` | `test_reader_cannot_import_or_run` |
| `test_api.py` | `APITests` | `test_analyst_cannot_forge_review` |
| `test_api.py` | `APITests` | `test_analyst_cannot_register_service_managed_verdict` |
| `test_api.py` | `APITests` | `test_cross_origin_request_rejected` |
| `test_api.py` | `APITests` | `test_unrecognized_host_rejected` |
| `test_api.py` | `APITests` | `test_invalid_request_fields_rejected` |
| `test_api.py` | `APITests` | `test_api_full_lifecycle_and_proof_download` |
| `test_api.py` | `APITests` | `test_frozen_parameters_cannot_be_overridden_at_run_time` |
| `test_api.py` | `APITests` | `test_frontend_has_restrictive_content_policy` |
| `test_api.py` | `APITests` | `test_path_traversal_has_no_static_file_route` |
| `test_api.py` | `APITests` | `test_request_pagination_validated` |
| `test_api.py` | `APITests` | `test_authenticated_identity_cannot_come_from_body` |
| `test_contracts.py` | `ContractTests` | `test_unknown_fields_rejected` |
| `test_contracts.py` | `ContractTests` | `test_bool_cannot_be_version` |
| `test_contracts.py` | `ContractTests` | `test_incompatible_enum_rejected` |
| `test_contracts.py` | `ContractTests` | `test_empty_proof_route_rejected` |
| `test_contracts.py` | `ContractTests` | `test_nonfinite_numbers_and_duplicate_keys_rejected` |
| `test_contracts.py` | `ContractTests` | `test_aware_datetime_required` |
| `test_contracts.py` | `ContractTests` | `test_reversed_time_interval_rejected` |
| `test_contracts.py` | `ContractTests` | `test_scope_narrowing_and_widening` |
| `test_contracts.py` | `ContractTests` | `test_scope_assumptions_have_conditional_direction` |
| `test_contracts.py` | `ContractTests` | `test_scope_partial_order_transitivity` |
| `test_contracts.py` | `ContractTests` | `test_dimension_conversion_preserves_raw` |
| `test_contracts.py` | `ContractTests` | `test_extract_nested_json_pointer_and_csv` |
| `test_contracts.py` | `ContractTests` | `test_no_arbitrary_transform_execution` |
| `test_contracts.py` | `ContractTests` | `test_normalization_does_not_claim_identity` |
| `test_contracts.py` | `ContractTests` | `test_evidence_strength_meet_is_not_average` |
| `test_contracts.py` | `ContractTests` | `test_immutable_object_and_audit_triggers` |
| `test_contracts.py` | `ContractTests` | `test_same_id_different_payload_is_rejected` |
| `test_contracts.py` | `ContractTests` | `test_ingest_is_idempotent` |
| `test_contracts.py` | `ContractTests` | `test_superseding_version_must_increase` |
| `test_contracts.py` | `ContractTests` | `test_evidence_fabrication_is_rejected` |
| `test_contracts.py` | `ContractTests` | `test_schema_has_required_fields_and_no_unknowns` |
| `test_gates.py` | `GateTests` | `test_gate_dag_rejects_circular_certification` |
| `test_gates.py` | `GateTests` | `test_gate_dag_rejects_missing_parent` |
| `test_gates.py` | `GateTests` | `test_failure_propagates_without_running_child` |
| `test_gates.py` | `GateTests` | `test_missing_gate_implementation_is_not_pass` |
| `test_gates.py` | `GateTests` | `test_all_ten_synthetic_scenarios` |
| `test_gates.py` | `GateTests` | `test_unfrozen_protocol_cannot_run` |
| `test_gates.py` | `GateTests` | `test_missing_identification_cannot_emit_causal_support` |
| `test_gates.py` | `GateTests` | `test_unsupported_association_is_not_intent` |
| `test_gates.py` | `GateTests` | `test_temporal_leak_blocks_historical_run` |
| `test_gates.py` | `GateTests` | `test_backdating_derived_evidence_rejected` |
| `test_gates.py` | `GateTests` | `test_market_per_decision_lookahead` |
| `test_gates.py` | `GateTests` | `test_scope_widening_is_blocked` |
| `test_gates.py` | `GateTests` | `test_evidence_valid_time_restricts_supporting_scope` |
| `test_gates.py` | `GateTests` | `test_negative_control_failure_invalidates_model` |
| `test_gates.py` | `GateTests` | `test_material_contradiction_blocks_promotion` |
| `test_gates.py` | `GateTests` | `test_new_contradiction_after_freeze_requires_amendment` |
| `test_gates.py` | `GateTests` | `test_source_echo_does_not_count_as_independence` |
| `test_gates.py` | `GateTests` | `test_source_corruption_is_a_runtime_block_not_falsification` |
| `test_gates.py` | `GateTests` | `test_counterfactual_sign_change_blocks_causal_promotion` |
| `test_gates.py` | `GateTests` | `test_counterfactual_cannot_change_inference_threshold` |
| `test_gates.py` | `GateTests` | `test_exploratory_protocol_cannot_be_promoted` |
| `test_gates.py` | `GateTests` | `test_disjunctive_route_can_survive_other_unresolved_claim` |
| `test_gates.py` | `GateTests` | `test_missing_mandatory_claim_cannot_be_averaged_away` |
| `test_gates.py` | `GateTests` | `test_weak_did_pretrend_rejects_identification` |
| `test_gates.py` | `GateTests` | `test_duplicate_sample_identity_rejected` |
| `test_gates.py` | `GateTests` | `test_causal_dag_required_and_cycles_rejected` |
| `test_gates.py` | `GateTests` | `test_declared_iv_exclusion_violation_cannot_pass` |
| `test_numerics.py` | `NumericalTests` | `test_mean_difference_known_answer` |
| `test_numerics.py` | `NumericalTests` | `test_bootstrap_seed_reproducibility` |
| `test_numerics.py` | `NumericalTests` | `test_bootstrap_resource_bounds` |
| `test_numerics.py` | `NumericalTests` | `test_holm_known_family` |
| `test_numerics.py` | `NumericalTests` | `test_bh_known_family` |
| `test_numerics.py` | `NumericalTests` | `test_uncontrolled_multiple_tests_rejected` |
| `test_numerics.py` | `NumericalTests` | `test_iv_recovers_exact_instrumented_effect` |
| `test_numerics.py` | `NumericalTests` | `test_constant_instrument_rejected` |
| `test_numerics.py` | `NumericalTests` | `test_linear_regression_known_answer` |
| `test_numerics.py` | `NumericalTests` | `test_did_known_effect_and_pretrend` |
| `test_numerics.py` | `NumericalTests` | `test_market_charges_initial_trade_and_borrow` |
| `test_numerics.py` | `NumericalTests` | `test_maxflow_min_cut_known_answer` |
| `test_numerics.py` | `NumericalTests` | `test_maxflow_disruption_changes_real_flow` |
| `test_numerics.py` | `NumericalTests` | `test_invalid_capacity_rejected` |
| `test_numerics.py` | `NumericalTests` | `test_science_incompatible_predictions_are_falsified` |
| `test_numerics.py` | `NumericalTests` | `test_physics_energy_and_recurrence` |
| `test_numerics.py` | `NumericalTests` | `test_no_universal_negative_from_failed_search` |
| `test_numerics.py` | `NumericalTests` | `test_unknown_adapter_parameter_not_ignored` |
| `test_numerics.py` | `NumericalTests` | `test_reproduction_tolerance_is_explicit` |
| `test_proof_review.py` | `ProofReviewTests` | `test_proof_roundtrip_reconstructs_full_gate_chain` |
| `test_proof_review.py` | `ProofReviewTests` | `test_proof_contains_required_reviewable_objects` |
| `test_proof_review.py` | `ProofReviewTests` | `test_modified_packet_member_detected` |
| `test_proof_review.py` | `ProofReviewTests` | `test_zip_path_traversal_rejected_before_extraction` |
| `test_proof_review.py` | `ProofReviewTests` | `test_restricted_source_blocks_public_export` |
| `test_proof_review.py` | `ProofReviewTests` | `test_packet_does_not_leak_unrelated_graph_ids` |
| `test_proof_review.py` | `ProofReviewTests` | `test_human_review_cannot_mutate_machine_verdict` |
| `test_proof_review.py` | `ProofReviewTests` | `test_release_requires_independent_reviewer` |
| `test_proof_review.py` | `ProofReviewTests` | `test_high_impact_requires_two_reviewers` |
| `test_proof_review.py` | `ProofReviewTests` | `test_hmac_authentication_detects_wrong_key_and_payload` |
| `test_proof_review.py` | `ProofReviewTests` | `test_reviewer_downgrade_blocks_release` |
| `test_proof_review.py` | `ProofReviewTests` | `test_failed_gate_prevents_release_despite_approval` |
| `test_proof_review.py` | `ProofReviewTests` | `test_backup_restore_preserves_objects_raw_and_audit` |
| `test_proof_review.py` | `ProofReviewTests` | `test_restore_cannot_overwrite_live_directory` |
| `test_proof_review.py` | `ProofReviewTests` | `test_corrupted_backup_is_rejected` |
| `test_quantifiers_closure.py` | `QuantifierClosureTests` | `test_exhaustive_finite_negative_is_certified_only_in_named_scope` |
| `test_quantifiers_closure.py` | `QuantifierClosureTests` | `test_incomplete_finite_coverage_cannot_certify_universal` |
| `test_quantifiers_closure.py` | `QuantifierClosureTests` | `test_single_valid_witness_falsifies_finite_universal_negative` |
| `test_quantifiers_closure.py` | `QuantifierClosureTests` | `test_universal_claim_requires_coverage_certificate` |
| `test_quantifiers_closure.py` | `QuantifierClosureTests` | `test_counterfactual_witness_blocks_certification` |
| `test_quantifiers_closure.py` | `QuantifierClosureTests` | `test_empty_search_is_not_a_universal_negative` |
| `test_quantifiers_closure.py` | `QuantifierClosureTests` | `test_existential_witness_has_no_universal_requirement` |
| `test_quantifiers_closure.py` | `QuantifierClosureTests` | `test_feedback_needs_ordered_bound_causal_edges_and_reproduces` |
| `test_quantifiers_closure.py` | `QuantifierClosureTests` | `test_bare_graph_cycle_does_not_certify_feedback` |
| `test_quantifiers_closure.py` | `QuantifierClosureTests` | `test_swapping_causal_edge_certificates_breaks_closure` |
| `test_quantifiers_closure.py` | `QuantifierClosureTests` | `test_chronologically_reversed_cycle_is_rejected` |

## Source Appendix F mapping

The PDF repeats ten test-purpose templates across TEST-001–TEST-080 while rotating illustrative PASS / FAIL-as-designed / BLOCKED-as-designed labels. Those labels are not mutually consistent execution oracles for the repeated prose. The mapping below preserves all 80 IDs and uses concrete semantic assertions in the modules, rather than fabricating 80 distinct specification cases.

| Source ID | Suite | Executable coverage |
|---|---|---|
| TEST-001 | schema | `test_contracts.py` |
| TEST-002 | provenance | `test_contracts.py; test_gates.py` |
| TEST-003 | scope | `test_contracts.py; test_quantifiers_closure.py` |
| TEST-004 | temporal | `test_gates.py; test_quantifiers_closure.py` |
| TEST-005 | gates | `test_gates.py` |
| TEST-006 | counterfactual | `test_gates.py; test_numerics.py` |
| TEST-007 | causal | `test_gates.py; test_numerics.py` |
| TEST-008 | closure | `test_quantifiers_closure.py` |
| TEST-009 | falsification | `test_gates.py; test_numerics.py` |
| TEST-010 | reproduction | `test_proof_review.py` |
| TEST-011 | schema | `test_contracts.py` |
| TEST-012 | provenance | `test_contracts.py; test_gates.py` |
| TEST-013 | scope | `test_contracts.py; test_quantifiers_closure.py` |
| TEST-014 | temporal | `test_gates.py; test_quantifiers_closure.py` |
| TEST-015 | gates | `test_gates.py` |
| TEST-016 | counterfactual | `test_gates.py; test_numerics.py` |
| TEST-017 | causal | `test_gates.py; test_numerics.py` |
| TEST-018 | closure | `test_quantifiers_closure.py` |
| TEST-019 | falsification | `test_gates.py; test_numerics.py` |
| TEST-020 | reproduction | `test_proof_review.py` |
| TEST-021 | schema | `test_contracts.py` |
| TEST-022 | provenance | `test_contracts.py; test_gates.py` |
| TEST-023 | scope | `test_contracts.py; test_quantifiers_closure.py` |
| TEST-024 | temporal | `test_gates.py; test_quantifiers_closure.py` |
| TEST-025 | gates | `test_gates.py` |
| TEST-026 | counterfactual | `test_gates.py; test_numerics.py` |
| TEST-027 | causal | `test_gates.py; test_numerics.py` |
| TEST-028 | closure | `test_quantifiers_closure.py` |
| TEST-029 | falsification | `test_gates.py; test_numerics.py` |
| TEST-030 | reproduction | `test_proof_review.py` |
| TEST-031 | schema | `test_contracts.py` |
| TEST-032 | provenance | `test_contracts.py; test_gates.py` |
| TEST-033 | scope | `test_contracts.py; test_quantifiers_closure.py` |
| TEST-034 | temporal | `test_gates.py; test_quantifiers_closure.py` |
| TEST-035 | gates | `test_gates.py` |
| TEST-036 | counterfactual | `test_gates.py; test_numerics.py` |
| TEST-037 | causal | `test_gates.py; test_numerics.py` |
| TEST-038 | closure | `test_quantifiers_closure.py` |
| TEST-039 | falsification | `test_gates.py; test_numerics.py` |
| TEST-040 | reproduction | `test_proof_review.py` |
| TEST-041 | schema | `test_contracts.py` |
| TEST-042 | provenance | `test_contracts.py; test_gates.py` |
| TEST-043 | scope | `test_contracts.py; test_quantifiers_closure.py` |
| TEST-044 | temporal | `test_gates.py; test_quantifiers_closure.py` |
| TEST-045 | gates | `test_gates.py` |
| TEST-046 | counterfactual | `test_gates.py; test_numerics.py` |
| TEST-047 | causal | `test_gates.py; test_numerics.py` |
| TEST-048 | closure | `test_quantifiers_closure.py` |
| TEST-049 | falsification | `test_gates.py; test_numerics.py` |
| TEST-050 | reproduction | `test_proof_review.py` |
| TEST-051 | schema | `test_contracts.py` |
| TEST-052 | provenance | `test_contracts.py; test_gates.py` |
| TEST-053 | scope | `test_contracts.py; test_quantifiers_closure.py` |
| TEST-054 | temporal | `test_gates.py; test_quantifiers_closure.py` |
| TEST-055 | gates | `test_gates.py` |
| TEST-056 | counterfactual | `test_gates.py; test_numerics.py` |
| TEST-057 | causal | `test_gates.py; test_numerics.py` |
| TEST-058 | closure | `test_quantifiers_closure.py` |
| TEST-059 | falsification | `test_gates.py; test_numerics.py` |
| TEST-060 | reproduction | `test_proof_review.py` |
| TEST-061 | schema | `test_contracts.py` |
| TEST-062 | provenance | `test_contracts.py; test_gates.py` |
| TEST-063 | scope | `test_contracts.py; test_quantifiers_closure.py` |
| TEST-064 | temporal | `test_gates.py; test_quantifiers_closure.py` |
| TEST-065 | gates | `test_gates.py` |
| TEST-066 | counterfactual | `test_gates.py; test_numerics.py` |
| TEST-067 | causal | `test_gates.py; test_numerics.py` |
| TEST-068 | closure | `test_quantifiers_closure.py` |
| TEST-069 | falsification | `test_gates.py; test_numerics.py` |
| TEST-070 | reproduction | `test_proof_review.py` |
| TEST-071 | schema | `test_contracts.py` |
| TEST-072 | provenance | `test_contracts.py; test_gates.py` |
| TEST-073 | scope | `test_contracts.py; test_quantifiers_closure.py` |
| TEST-074 | temporal | `test_gates.py; test_quantifiers_closure.py` |
| TEST-075 | gates | `test_gates.py` |
| TEST-076 | counterfactual | `test_gates.py; test_numerics.py` |
| TEST-077 | causal | `test_gates.py; test_numerics.py` |
| TEST-078 | closure | `test_quantifiers_closure.py` |
| TEST-079 | falsification | `test_gates.py; test_numerics.py` |
| TEST-080 | reproduction | `test_proof_review.py` |
