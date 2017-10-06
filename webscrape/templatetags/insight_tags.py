from django import template

''' TEMPLATE FILTERS 
********************************************************************************
'''
register = template.Library()


def isfloat(x):
  try:
    a = float(x)
  except ValueError:
    return False
  else:
    return True

def isint(x):
  try:
    a = float(x)
    b = int(a)
  except ValueError:
    return False
  else:
    return a == b

@register.filter
def percentage(value, precision=3):
  return format(float(value), "." + str(precision) + "%")
    
@register.filter
def percentiffloat(value):
  if isint(value):
    return int(value)
  elif isfloat(value):
    return format(float(value), ".3%")
  else: 
    return 0
    
@register.filter
def intorfloat(value, precision=3):
  if isint(value):
    return int(value)
  elif isfloat(value):
    return format(float(value), "." + str(precision) + "f")
  else: 
    return 0