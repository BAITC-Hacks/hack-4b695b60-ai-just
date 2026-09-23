import type { ReactNode } from "react";
import { Select as Primitive } from "radix-ui";
import { Check, ChevronDown, ChevronUp } from "lucide-react";

type SelectOption<T extends string> = {
  value: T;
  label: string;
  disabled?: boolean;
};

export function Select<T extends string>({
  value,
  onValueChange,
  options,
  label,
  id,
  className = "",
  disabled = false,
  icon,
}: {
  value: T;
  onValueChange: (value: T) => void;
  options: readonly SelectOption<T>[];
  label: string;
  id?: string;
  className?: string;
  disabled?: boolean;
  icon?: ReactNode;
}) {
  // Prefix every value so an explicit “all / optional” choice can use an empty string.
  const encoded = (option: string) => `option:${option}`;
  return (
    <Primitive.Root
      value={encoded(value)}
      disabled={disabled}
      onValueChange={(next) => {
        const option = options.find((item) => encoded(item.value) === next);
        if (option && !option.disabled) onValueChange(option.value);
      }}
    >
      <Primitive.Trigger
        id={id}
        className={`select-trigger ${className}`}
        aria-label={label}
      >
        {icon && (
          <span className="select-leading-icon" aria-hidden="true">
            {icon}
          </span>
        )}
        <span className="select-value">
          <Primitive.Value />
        </span>
        <Primitive.Icon className="select-chevron">
          <ChevronDown size={15} aria-hidden="true" />
        </Primitive.Icon>
      </Primitive.Trigger>
      <Primitive.Portal>
        <Primitive.Content
          className="select-menu"
          position="popper"
          sideOffset={7}
          collisionPadding={12}
          align="start"
        >
          <Primitive.ScrollUpButton className="select-scroll">
            <ChevronUp size={15} aria-hidden="true" />
          </Primitive.ScrollUpButton>
          <Primitive.Viewport className="select-viewport">
            <Primitive.Group>
              <Primitive.Label className="select-label">
                {label}
              </Primitive.Label>
              {options.map((option) => (
                <Primitive.Item
                  key={option.value}
                  value={encoded(option.value)}
                  disabled={option.disabled}
                  textValue={option.label}
                  className="select-option"
                >
                  <Primitive.ItemText>{option.label}</Primitive.ItemText>
                  <Primitive.ItemIndicator className="select-check">
                    <Check size={16} aria-hidden="true" />
                  </Primitive.ItemIndicator>
                </Primitive.Item>
              ))}
            </Primitive.Group>
          </Primitive.Viewport>
          <Primitive.ScrollDownButton className="select-scroll">
            <ChevronDown size={15} aria-hidden="true" />
          </Primitive.ScrollDownButton>
        </Primitive.Content>
      </Primitive.Portal>
    </Primitive.Root>
  );
}
