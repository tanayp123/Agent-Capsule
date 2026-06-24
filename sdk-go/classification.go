package agentcapsule

import "reflect"

var fieldNameDataClasses = map[string]string{
	"account_id":          "account_id",
	"account_notes":       "account_notes",
	"api_key":             "secrets",
	"claim_notes":         "account_notes",
	"customer_id":         "customer_identifier",
	"document":            "document_text",
	"email":               "email",
	"medical_information": "medical_information",
	"notes":               "account_notes",
	"policy_number":       "policy_number",
	"prompt":              "prompt_content",
	"support_tier":        "support_tier",
	"user_id":             "user_identifier",
}

func ClassifyPayload(value any) []string {
	classes := map[string]bool{}
	classifyInto(reflect.ValueOf(value), "", classes)
	output := []string{}
	for dataClass := range classes {
		output = append(output, dataClass)
	}
	return sortedUnique(output)
}

func classifyInto(value reflect.Value, fieldName string, classes map[string]bool) {
	if fieldName != "" {
		if dataClass := fieldNameDataClasses[fieldName]; dataClass != "" {
			classes[dataClass] = true
		}
	}
	if !value.IsValid() {
		return
	}
	if value.Kind() == reflect.Pointer || value.Kind() == reflect.Interface {
		if value.IsNil() {
			return
		}
		classifyInto(value.Elem(), fieldName, classes)
		return
	}
	switch value.Kind() {
	case reflect.Map:
		for _, key := range value.MapKeys() {
			classifyInto(value.MapIndex(key), key.String(), classes)
		}
	case reflect.Slice, reflect.Array:
		for i := 0; i < value.Len(); i++ {
			classifyInto(value.Index(i), "", classes)
		}
	case reflect.Struct:
		valueType := value.Type()
		for i := 0; i < value.NumField(); i++ {
			field := valueType.Field(i)
			if !field.IsExported() {
				continue
			}
			if tag := field.Tag.Get("capsule"); tag != "" {
				classes[tag] = true
			}
			classifyInto(value.Field(i), fieldNameFromStruct(field), classes)
		}
	}
}

func fieldNameFromStruct(field reflect.StructField) string {
	if tag := field.Tag.Get("json"); tag != "" && tag != "-" {
		for i, char := range tag {
			if char == ',' {
				return tag[:i]
			}
		}
		return tag
	}
	return field.Name
}
