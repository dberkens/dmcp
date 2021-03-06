from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

__author__ = "Xinyue"
import cvxpy as cvx
import numpy as np
from cvxpy.expressions.expression import Expression
from cvxpy.problems.problem import Problem
from cvxpy.expressions.variable import Variable
from cvxpy.constraints.nonpos import NonPos, NonNeg, Inequality
from cvxpy.constraints.psd import PSD


def fix(obj, fix_vars):
    """Fix the given variables in the object.
        Parameters
        ----------
        obj : Problem or expression
        fix_var : List or variable
            Variables to be fixed.
        Returns
        -------
        Problem or expression
    """

    # Test whether fix_vars is already list, if not, recast
    if not isinstance(fix_vars, list):
        fix_vars = [fix_vars]

    # Create list of parameters
    variable_list = obj.variables()
    variable_list.sort(key=lambda x: x.id)
    param_list = []
    for var in variable_list:
        if var.sign == "NONNEGATIVE":
            para = cvx.Parameter(shape=var.shape, nonneg=True)
            if var.value is not None:
                para.value = abs(var.value)
        elif var.sign == "NONPOSITIVE":
            para = cvx.Parameter(shape=var.shape, nonpos=True)
            if var.value is not None:
                para.value = -abs(var.value)
        elif var.attributes["PSD"] is True:
            para = cvx.Parameter(shape=var.shape, PSD=True)
            if var.value is not None:
                para.value = var.value
        else:
            para = cvx.Parameter(shape=var.shape)
            if var.value is not None:
                para.value = var.value
        if var.value is None:
            para.value = np.zeros(var.shape)
        para.id = var.id
        param_list.append(para)

    param_list.sort(key=lambda x: x.id)
    if isinstance(obj, Expression):
        return fix_expr(obj, fix_vars, param_list)
    elif isinstance(obj, Problem):
        return fix_prob(obj, fix_vars, param_list)
    else:
        print("wrong type to fix")


def fix_prob(prob, fix_var, param_list):
    """Fix the given variables in the problem.
        Parameters
        ----------
        expr : Problem
        fix_var : List
            Variables to be fixed.
        params: : List
            List of parameters to replace variables from fix_var
        Returns
        -------
        Problem
        """
    new_cost = fix_expr(prob.objective.expr, fix_var, param_list)
    if prob.objective.NAME == "minimize":
        new_obj = cvx.Minimize(new_cost)
    else:
        new_obj = cvx.Maximize(new_cost)
    new_constr = []
    for con in prob.constraints:
        if isinstance(con, Inequality):
            lhs = fix_expr(con.args[0], fix_var, param_list)
            rhs = fix_expr(con.args[1], fix_var, param_list)
            new_constr.append(lhs <= rhs)
        else:
            fix_con = fix_expr(con.expr, fix_var, param_list)
            if isinstance(con, NonPos):
                new_constr.append(fix_con <= 0)
            elif isinstance(con, NonNeg):
                new_constr.append(fix_con >= 0)
            elif isinstance(con, PSD):
                new_constr.append(fix_con >> 0)
            else:
                new_constr.append(fix_con == 0)
    new_prob = Problem(new_obj, new_constr)
    return new_prob


def fix_expr(expr, fix_var, param_list):
    """Fix the given variables in the expression.
        Parameters
        ----------
        expr : Expression
        fix_var : List
            Variables to be fixed.
        params : List
            List of parameters to replace variables from fix_var
        Returns
        -------
        Expression
    """
    fix_var_id = [var.id for var in fix_var]
    fix_var_id.sort()
    if isinstance(expr, Variable) and expr.id in fix_var_id:
        param = next(
            (
                temp_param
                for temp_param in param_list
                if temp_param.id == expr.id
            ),
            None,
        )
        return param
    elif len(expr.args) == 0:
        return expr
    else:
        new_args = []
        for arg in expr.args:
            new_args.append(fix_expr(arg, fix_var, param_list))
        return expr.copy(args=new_args)
