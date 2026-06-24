package dev.agentcapsule;

import java.lang.reflect.Field;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.TreeSet;

public final class FieldClassifier {
    private static final Map<String, String> FIELD_NAME_DATA_CLASSES = Map.ofEntries(
            Map.entry("account_id", "account_id"),
            Map.entry("account_notes", "account_notes"),
            Map.entry("api_key", "secrets"),
            Map.entry("claim_notes", "account_notes"),
            Map.entry("customer_id", "customer_identifier"),
            Map.entry("document", "document_text"),
            Map.entry("email", "email"),
            Map.entry("medical_information", "medical_information"),
            Map.entry("notes", "account_notes"),
            Map.entry("policy_number", "policy_number"),
            Map.entry("prompt", "prompt_content"),
            Map.entry("support_tier", "support_tier"),
            Map.entry("user_id", "user_identifier")
    );

    private FieldClassifier() {
    }

    public static List<String> classify(Object value) {
        TreeSet<String> classes = new TreeSet<>();
        classifyInto(value, "", classes);
        return new ArrayList<>(classes);
    }

    private static void classifyInto(Object value, String fieldName, Collection<String> classes) {
        if (fieldName != null && !fieldName.isBlank()) {
            String dataClass = FIELD_NAME_DATA_CLASSES.get(fieldName.toLowerCase());
            if (dataClass != null) {
                classes.add(dataClass);
            }
        }
        if (value == null || value instanceof String || value instanceof Number || value instanceof Boolean) {
            return;
        }
        if (value instanceof Map<?, ?> map) {
            for (Map.Entry<?, ?> entry : map.entrySet()) {
                classifyInto(entry.getValue(), String.valueOf(entry.getKey()), classes);
            }
            return;
        }
        if (value instanceof Iterable<?> iterable) {
            for (Object item : iterable) {
                classifyInto(item, "", classes);
            }
            return;
        }
        for (Field field : value.getClass().getDeclaredFields()) {
            field.setAccessible(true);
            DataClass annotation = field.getAnnotation(DataClass.class);
            if (annotation != null) {
                classes.addAll(List.of(annotation.value()));
            }
            try {
                classifyInto(field.get(value), field.getName(), classes);
            } catch (IllegalAccessException ignored) {
                // Reflection access was already requested; inaccessible fields are skipped safely.
            }
        }
    }
}
