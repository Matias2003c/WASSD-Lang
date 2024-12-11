from os.path import dirname, join
from textx import metamodel_from_file, TextXSyntaxError
from textx.export import metamodel_export, model_export


class WASSDInterpreter:
    def __init__(self):
        self.variables = {}
        self.functions = {}

    def interpret(self, model):
        for statement in model.statements:
            if statement.__class__.__name__ == "VariableDeclaration":
                val = self.evaluate_expression(statement.val)
                self.variables[statement.var] = val

            elif statement.__class__.__name__ == "Print":
                val = self.variables.get(statement.var, None)
                if val is None:
                    print(f"Error: Variable '{statement.var}' not declared.")
                else:
                    print(val)

            elif statement.__class__.__name__ == "WhileLoop":
                while self.evaluate_comparison(statement.condition):
                    for stmt in statement.statements:
                        self.interpret_loop(stmt)
            
            elif statement.__class__.__name__ == "ForLoop":
                self.execute_for_loop(statement)

            elif statement.__class__.__name__ == "Conditional":
                self.execute_conditional(statement)

            elif statement.__class__.__name__ == "FunctionDeclaration":
                self.declare_function(statement)

            elif statement.__class__.__name__ == "FunctionCall":
                self.call_function(statement)

    def declare_function(self, statement):
        # Save the function definition, with parameters and body
        self.functions[statement.name] = {
            "params": statement.params,
            "statements": statement.statements,
        }

    def call_function(self, statement):
        func = self.functions.get(statement.name)
        if not func:
            raise ValueError(f"Error: Function '{statement.name}' not declared.")
        
        # Validate the number of arguments
        if len(func["params"]) != len(statement.args):
            raise ValueError(f"Error: Function '{statement.name}' expects {len(func['params'])} arguments but got {len(statement.args)}.")
        
        # Map arguments to parameters
        local_vars = self.variables.copy()
        for param, arg in zip(func["params"], statement.args):
            local_vars[param] = self.evaluate_expression(arg)
        
        # Execute function body in the local context
        original_vars = self.variables
        self.variables = local_vars
        try:
            for stmt in func["statements"]:
                self.interpret_loop(stmt)
        finally:
            self.variables = original_vars
    
    
    def execute_conditional(self, statement):
        # Evaluate the condition of the conditional
        if self.evaluate_comparison(statement.condition):
            # If the condition is true, execute the first block of statements
            for stmt in statement.statements:
                self.interpret_loop(stmt)

            # Optionally, execute the else block if present
        elif statement.elseStmt:
            for stmt in statement.elseStmt:
                self.interpret_loop(stmt)

    def execute_for_loop(self, statement):
        # Initialize the loop variable from the declaration
        var = statement.var
        # Set the initial value of the loop variable
        self.variables[var] = self.evaluate_factor(statement.condition.left)

        # Determine the condition expression (this assumes the condition is a comparison)
        condition = statement.condition
        # The step is evaluated once before the loop starts
        step = self.evaluate_factor(statement.step)

        # Loop until the condition evaluates to False
        while self.evaluate_comparison(condition):
            for stmt in statement.statements:
                self.interpret_loop(stmt)

            # After executing the loop body, apply the step to the loop variable
            self.variables[var] += step  # Increment or modify the loop variable by the step
            # Reevaluate the condition after the change
            condition.left = self.evaluate_factor(var)
    
    def interpret_loop(self, statement):
        if statement.__class__.__name__ == "VariableDeclaration":
            val = self.evaluate_expression(statement.val)
            self.variables[statement.var] = val

        elif statement.__class__.__name__ == "Print":
            val = self.variables.get(statement.var, None)
            if val is None:
                print(f"Error: Variable '{statement.var}' not declared.")
            else:
                print(val)

        elif statement.__class__.__name__ == "WhileLoop":
            while self.evaluate_comparison(statement.condition):
                    for stmt in statement.statements:
                        self.interpret_loop(stmt)
                    
        elif statement.__class__.__name__ == "ForLoop":
                self.execute_for_loop(statement)

        elif statement.__class__.__name__ == "Conditional":
                self.execute_conditional(statement)
    
    def evaluate_comparison(self, comparison):

        left = self.evaluate_factor(comparison.left)
        right = self.evaluate_factor(comparison.right)
        operator = comparison.operator

        if operator == "wff":  # Greater than
            return left > right
        elif operator == "sff":  # Less than
            return left < right
        elif operator == "Ff":  # Not equal
            return left != right
        elif operator == "FF":  # Equal
            return left == right
        else:
            raise ValueError(f"Invalid comparison operator: {operator}")
    
    def evaluate_expression(self, expr):
        # Start with the left operand
        result = self.evaluate_factor(expr.left)

        for i in range(len(expr.right)):
            operator = expr.op[i]  # Get the operator from the expression
            right_value = self.evaluate_factor(expr.right[i])  # Get the right operand

            # Perform the operation based on the operator
            if operator == "w":  # Addition
                result += right_value
            elif operator == "s":  # Subtraction
                result -= right_value
            elif operator == "a":  # Multiplication
                result *= right_value
            elif operator == "d":  # Division
                result = result / right_value if isinstance(result, float) or isinstance(right_value, float) else result // right_value
            elif operator == "Da":  # Modulo
                result %= right_value
            elif operator == "Ad":  # Exponentiation
                result **= right_value

            if isinstance(result, float) and result.is_integer():
                result = int(result)
            elif isinstance(result, float): 
                result = float("{:.4f}".format(result))

        return result
    
    def evaluate_factor(self, factor):
        if isinstance(factor, float):
            if factor.is_integer():
                factor = int(factor)
            return factor
        elif isinstance(factor, str):
            if factor.isdigit():
                return int(factor)
            elif factor.replace('.', '', 1).isdigit() and not factor.startswith('.') and not factor.endswith('.'):
                return float(factor)
            elif factor in self.variables:
                return self.variables[factor]
            elif issubclass(type(factor), str):
                return factor
            else:
                raise ValueError(f"Error: Variable '{factor}' is not defined.")
        elif isinstance(factor, int) or isinstance(factor, float):
            return factor
        else:
            raise ValueError(f"Invalid factor: {factor}")

def main(debug=False):
    this_folder = dirname(__file__)

    try:
        wassd_mm = metamodel_from_file(join(this_folder, 'WASSD.tx'), debug=debug)
        metamodel_export(wassd_mm, join(this_folder, 'wassd_meta.dot'))

        wassd_model = wassd_mm.model_from_file(join(this_folder, 'program.wassd'))
        model_export(wassd_model, join(this_folder, 'wassd_model.dot'))

        interpreter = WASSDInterpreter()
        interpreter.interpret(wassd_model)

    except TextXSyntaxError as e:
        print(f"Syntax error: {e}")


if __name__ == "__main__":
    main()